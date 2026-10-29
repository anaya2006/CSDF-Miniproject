"""Frame analysis, audio-level analysis, Chrome-playable preview and A-vs-B comparison."""
import os, base64, shutil, subprocess
import cv2, numpy as np
from flask import Blueprint, request, jsonify, current_app

x = Blueprint('x', __name__)
SR, WIN = 16000, 800            # analysis sample-rate; 50 ms level window
db = lambda v: 20 * np.log10(np.maximum(v, 1e-6))


def ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which('ffmpeg')


def path_of(fn):
    p = os.path.join(current_app.config['UPLOAD_FOLDER'], os.path.basename(fn or ''))
    return p if os.path.isfile(p) else None


def ds(a, fn=np.mean, k=600):
    a = np.asarray(a, float)
    if len(a) > k:
        a = np.array([fn(q) for q in np.array_split(a, k)])
    return [round(float(v), 3) for v in a]


def runs(mask, minlen=1):
    out, s = [], None
    for i, v in enumerate(list(mask) + [False]):
        if v and s is None: s = i
        if not v and s is not None:
            if i - s >= minlen: out.append((s, i))
            s = None
    return out


# ── Chrome-friendly preview (H.264/AAC) ──────────────────────────────────────
@x.route('/playable', methods=['POST'])
def playable():
    fn = os.path.basename(request.json.get('filename', '')); p = path_of(fn); ff = ffmpeg()
    if not p: return jsonify(error='File not found'), 404
    orig = {'url': '/static/uploads/' + fn, 'transcoded': False}
    if not ff: return jsonify(orig)
    out = os.path.splitext(fn)[0] + '_web.mp4'; op = os.path.join(current_app.config['UPLOAD_FOLDER'], out)
    if not os.path.exists(op):
        r = subprocess.run([ff, '-y', '-v', 'error', '-i', p, '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28',
                            '-pix_fmt', 'yuv420p', '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2', '-c:a', 'aac',
                            '-movflags', '+faststart', op], capture_output=True)
        if r.returncode: return jsonify(orig)
    return jsonify(url='/static/uploads/' + out, transcoded=True)


# ── Frame scan ───────────────────────────────────────────────────────────────
def scan(p, cap=4000):
    c = cv2.VideoCapture(p)
    if not c.isOpened(): return None
    fps = c.get(cv2.CAP_PROP_FPS) or 25.0
    st = max(1, int(c.get(cv2.CAP_PROP_FRAME_COUNT)) // cap); fr, i = [], 0
    while c.grab():
        if i % st == 0:
            ok, f = c.retrieve()
            if ok: fr.append(cv2.cvtColor(cv2.resize(f, (160, 90), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY))
        i += 1
    c.release()
    return {'fps': fps, 'n': i, 'st': st, 'f': np.array(fr), 'dur': i / fps} if fr else None


@x.route('/frame_analysis', methods=['POST'])
def frame_analysis():
    p = path_of(request.json.get('filename')); s = p and scan(p)
    if not s: return jsonify(error='Cannot decode video'), 400
    f = s['f'].astype(np.float32)
    d = np.insert(np.abs(np.diff(f, axis=0)).mean((1, 2)), 0, 0)
    br = f.mean((1, 2)); sh = np.array([cv2.Laplacian(g, cv2.CV_32F).var() for g in s['f']])
    th = max(d.mean() + 4 * d.std(), 12)
    return jsonify(total=s['n'], fps=round(s['fps'], 3), dur=round(s['dur'], 3), stride=s['st'],
                   cuts=[round(float(i * s['st'] / s['fps']), 2) for i in np.where(d > th)[0]][:60],
                   dups=int((d[1:] < 0.05).sum()), blurry=int((sh < 0.25 * np.median(sh)).sum()),
                   avg_b=round(float(br.mean()), 1), diff=ds(d, np.max), bright=ds(br), sharp=ds(sh))


# ── Audio ────────────────────────────────────────────────────────────────────
def decode_audio(p):
    ff = ffmpeg()
    if not ff: return None
    r = subprocess.run([ff, '-v', 'error', '-i', p, '-vn', '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'], capture_output=True)
    return np.frombuffer(r.stdout, np.int16).astype(np.float32) / 32768 if len(r.stdout) > WIN * 2 else None


def levels(a):
    n = len(a) // WIN
    return db(np.sqrt((a[:n * WIN].reshape(n, WIN) ** 2).mean(1))) if n else np.array([-120.])


def bands(a):
    k = len(a) // 2048
    if k < 1: return []
    S = np.abs(np.fft.rfft(a[:k * 2048].reshape(k, 2048) * np.hanning(2048), axis=1)).mean(0)
    e = np.unique(np.geomspace(6, 1000, 25).astype(int))
    return [round(float(db(S[e[i]:e[i + 1]].mean() / 32)), 1) for i in range(len(e) - 1)]


def astats(a):
    r = levels(a); pk = float(db(np.abs(a).max())); rms = float(db(np.sqrt((a ** 2).mean()))); live = r[r > -60]; W = 800
    k = max(1, len(a) // W); w = a[:k * W].reshape(-1, k)
    return dict(has_audio=True, dur=round(len(a) / SR, 2), peak=round(pk, 1), rms=round(rms, 1), crest=round(pk - rms, 1),
                clip=round(float((np.abs(a) >= 0.999).mean() * 100), 3), dc=round(float(a.mean()), 5),
                silence=round(float((r < -50).mean() * 100), 1),
                dyn=round(float(np.percentile(live, 95) - np.percentile(live, 5)), 1) if len(live) > 1 else 0,
                jumps=[round(i * .05, 2) for i in np.where(np.abs(np.diff(r)) > 30)[0]][:20],
                gaps=[round(s * .05, 2) for s, _ in runs(r < -100, 2)][:20],
                rms_db=ds(r), wmin=[round(float(v), 3) for v in w.min(1)], wmax=[round(float(v), 3) for v in w.max(1)],
                bands=bands(a))


@x.route('/audio_analysis', methods=['POST'])
def audio_analysis():
    p = path_of(request.json.get('filename'))
    if not p: return jsonify(error='File not found'), 404
    if not ffmpeg(): return jsonify(error='ffmpeg not available - run: pip install imageio-ffmpeg'), 500
    a = decode_audio(p)
    return jsonify(astats(a) if a is not None else {'has_audio': False})


# ── Compare ──────────────────────────────────────────────────────────────────
def ssim(a, b):
    a, b = a.astype(np.float32), b.astype(np.float32); g = lambda z: cv2.GaussianBlur(z, (7, 7), 1.5)
    ma, mb = g(a), g(b); va, vb, c = g(a * a) - ma * ma, g(b * b) - mb * mb, g(a * b) - ma * mb
    return float((((2 * ma * mb + 6.5) * (2 * c + 58.5)) / ((ma * ma + mb * mb + 6.5) * (va + vb + 58.5))).mean())


def safe_corr(a, b):
    if len(a) < 2 or a.std() == 0 or b.std() == 0: return 0.0
    return float(np.nan_to_num(np.corrcoef(a, b)[0, 1]))


@x.route('/compare', methods=['POST'])
def compare():
    j = request.json; pa, pb = path_of(j.get('a')), path_of(j.get('b'))
    if not (pa and pb): return jsonify(error='Upload both videos first'), 404
    M = current_app.config['META_FN']; ma, mb = M(pa), M(pb); F = []
    add = lambda sev, t: F.append({'sev': sev, 'text': t})
    rows = [[k, ma.get(k), mb.get(k), ma.get(k) != mb.get(k)] for k in
            ('md5', 'sha256', 'file_size', 'duration_seconds', 'frame_count', 'fps', 'width', 'height', 'codec')]
    for src in ('mutagen_extra', 'mutagen_tags'):
        ea, eb = ma.get(src, {}), mb.get(src, {})
        rows += [[k, ea.get(k), eb.get(k), ea.get(k) != eb.get(k)] for k in sorted(set(ea) | set(eb))]
    if ma['sha256'] == mb['sha256']:
        return jsonify(verdict='IDENTICAL', level='ok', score=0, rows=rows, dur=0, frames={'t': [], 'ssim': [], 'mae': []},
                       audio=None, findings=[{'sev': 'INFO', 'text': 'SHA-256 and MD5 match: the files are bit-for-bit identical.'}])
    add('INFO', 'File hashes differ - the files are not byte-identical.')
    if abs(ma['duration_seconds'] - mb['duration_seconds']) > .2:
        add('HIGH', f"Duration differs: A={ma['duration_seconds']}s, B={mb['duration_seconds']}s - video trimmed, extended or spliced.")
    if (ma['width'], ma['height']) != (mb['width'], mb['height']): add('MEDIUM', 'Resolution differs - rescaled or cropped.')
    if abs(ma['fps'] - mb['fps']) > .01: add('MEDIUM', f"Frame rate differs ({ma['fps']} vs {mb['fps']}).")
    if ma['codec'] != mb['codec']: add('INFO', f"Codec tag differs ({ma['codec']} vs {mb['codec']}) - file was re-encoded/re-muxed.")
    A, B = scan(pa), scan(pb)
    if not A or not B: return jsonify(error='Cannot decode one of the videos'), 400
    dur = min(A['dur'], B['dur']); n = int(min(300, max(2, dur * 5))); ts = np.linspace(0, max(dur - .05, 0), n)
    ia = [min(len(A['f']) - 1, int(t * A['fps'] / A['st'])) for t in ts]; ib = [min(len(B['f']) - 1, int(t * B['fps'] / B['st'])) for t in ts]
    ss = np.array([ssim(A['f'][a], B['f'][b]) for a, b in zip(ia, ib)])
    mae = np.array([np.abs(A['f'][a].astype(float) - B['f'][b]).mean() for a, b in zip(ia, ib)])
    bright = float(np.mean([B['f'][b].mean() - A['f'][a].mean() for a, b in zip(ia, ib)]))
    sm = lambda S, ix: np.array([cv2.resize(S['f'][i], (32, 18), interpolation=cv2.INTER_AREA) for i in ix], np.float32)
    SA, SB = sm(A, ia), sm(B, ib); K = n // 4
    err = lambda s: np.abs(SA[max(0, -s):n - max(0, s)] - SB[max(0, s):n - max(0, -s)]).mean() if abs(s) < n else 1e9
    best = min(range(-K, K + 1), key=err); step = float(ts[1] - ts[0]) if n > 1 else 1
    if ss.mean() < .9 and best and err(best) < .5 * err(0):
        add('HIGH', f'B matches A when shifted by {best * step:+.1f}s - content was trimmed or inserted near the start.')
    elif ss.mean() < .985 and (ss < .97).mean() > .8:
        add('MEDIUM', f'Whole-video change (mean SSIM {ss.mean():.3f}) - re-encode, filter, colour grade or rescale.')
    else:
        for s, e in runs(ss < .97, 2)[:8]:
            add('HIGH', f'Localised visual change {ts[s]:.1f}s-{ts[min(e, n - 1)]:.1f}s (min SSIM {ss[s:e].min():.3f}) - possible overlay, edit or splice.')
    if abs(bright) > 3: add('MEDIUM', f'Average brightness shifted by {bright:+.1f} levels (0-255).')
    au = None; a1, b1 = decode_audio(pa), decode_audio(pb)
    if (a1 is None) != (b1 is None):
        add('HIGH', 'Audio track exists in only one file (' + ('A' if a1 is not None else 'B') + ' has audio) - audio removed or added.')
    elif a1 is not None:
        ra, rb = levels(a1), levels(b1); m = min(len(ra), len(rb)); d = rb[:m] - ra[:m]; ok = (ra[:m] > -60) & (rb[:m] > -60)
        gain = float(np.median(d[ok])) if ok.any() else 0.0; ec = safe_corr(ra[:m], rb[:m]); L = min(len(a1), len(b1)); sc = safe_corr(a1[:L], b1[:L])
        if abs(len(a1) - len(b1)) / SR > .2: add('HIGH', f'Audio length differs by {abs(len(a1) - len(b1)) / SR:.2f}s.')
        if abs(gain) > .5: add('MEDIUM', f'Overall audio level changed by {gain:+.1f} dB.')
        for s, e in runs(ok & (np.abs(d - gain) > 3), 10)[:6]:
            add('HIGH', f'Local audio level change {s * .05:.1f}s-{e * .05:.1f}s ({d[s:e].mean() - gain:+.1f} dB relative to the rest) - possible edit, mute or overdub.')
        if sc < .9 and ec < .9: add('HIGH', f'Audio waveform differs (sample correlation {sc:.2f}, envelope {ec:.2f}) - audio replaced or heavily edited.')
        sa, sb = astats(a1), astats(b1)
        if sb['clip'] > sa['clip'] + .1: add('MEDIUM', f"Clipping increased from {sa['clip']}% to {sb['clip']}%.")
        au = dict(rmsA=ds(ra), rmsB=ds(rb), diff=ds(d), bandsA=sa['bands'], bandsB=sb['bands'], gain=round(gain, 2), env_corr=round(ec, 3), corr=round(sc, 3),
                  dur=round(min(len(a1), len(b1)) / SR, 2), A={k: sa[k] for k in ('peak', 'rms', 'clip', 'silence', 'dyn')}, B={k: sb[k] for k in ('peak', 'rms', 'clip', 'silence', 'dyn')})
    hi = any(f['sev'] == 'HIGH' for f in F); mid = any(f['sev'] == 'MEDIUM' for f in F)
    return jsonify(verdict='MODIFIED - content differs' if hi else 'RE-ENCODED / MINOR CHANGES' if mid else 'EQUIVALENT CONTENT (different bytes)',
                   level='bad' if hi else 'warn' if mid else 'ok', score=round(100 * (1 - float(ss.mean())), 1), findings=F, rows=rows,
                   dur=round(dur, 2), frames={'t': [round(float(t), 2) for t in ts], 'ssim': [round(float(v), 4) for v in ss], 'mae': [round(float(v), 2) for v in mae]}, audio=au)


@x.route('/compare_frame', methods=['POST'])
def compare_frame():
    j = request.json; t = float(j.get('t', 0)); fr = []
    for k in 'ab':
        p = path_of(j.get(k)); c = cv2.VideoCapture(p) if p else None
        if not c or not c.isOpened(): return jsonify(error='File not found'), 404
        c.set(cv2.CAP_PROP_POS_FRAMES, int(t * (c.get(cv2.CAP_PROP_FPS) or 25))); ok, f = c.read(); c.release()
        if not ok: return jsonify(error='No frame at that time'), 400
        fr.append(f)
    a, b = fr[0], cv2.resize(fr[1], (fr[0].shape[1], fr[0].shape[0])); d = cv2.absdiff(a, b).max(2)
    heat = cv2.applyColorMap(np.clip(d.astype(np.float32) * 4, 0, 255).astype(np.uint8), cv2.COLORMAP_JET)
    enc = lambda im: 'data:image/jpeg;base64,' + base64.b64encode(cv2.imencode('.jpg', cv2.resize(im, (640, int(640 * im.shape[0] / im.shape[1]))), [cv2.IMWRITE_JPEG_QUALITY, 85])[1]).decode()
    return jsonify(a=enc(a), b=enc(b), diff=enc(heat), pct=round(float((d > 25).mean() * 100), 2))