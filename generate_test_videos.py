import os
import io
import sys
import json
import time
import base64
import shutil
import struct
import zipfile
import argparse

import cv2
import numpy as np

WIDTH, HEIGHT = 320, 240
FPS = 10
SECONDS = 5
RNG = np.random.default_rng(1337)


# ─── BASE VIDEO ───────────────────────────────────────────────────────────────

def make_frame(i, total, label):
    """Colourful moving-shapes frame with light noise (keeps LSB plane ~0.5)."""
    t = i / max(total - 1, 1)
    frame = np.zeros((HEIGHT, WIDTH, 3), np.uint8)
    # gradient background
    xs = np.linspace(0, 255, WIDTH, dtype=np.uint8)
    frame[:, :, 0] = xs[None, :]
    frame[:, :, 1] = np.linspace(40, 200, HEIGHT, dtype=np.uint8)[:, None]
    frame[:, :, 2] = int(80 + 100 * t)
    # moving shapes
    cx = int(30 + t * (WIDTH - 60))
    cv2.circle(frame, (cx, 90), 28, (0, 220, 255), -1)
    cv2.rectangle(frame, (WIDTH - cx - 25, 150), (WIDTH - cx + 25, 200), (255, 80, 120), -1)
    cv2.putText(frame, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(frame, f"frame {i:03d}  t={i / FPS:4.1f}s", (10, HEIGHT - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    noise = RNG.integers(-6, 7, frame.shape, dtype=np.int16)
    return np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)


def write_video(path, label, fourcc_candidates, frame_hook=None):
    """Write a video trying each fourcc until one opens. Returns fourcc used."""
    total = FPS * SECONDS
    for cc in fourcc_candidates:
        fourcc = 0 if cc == 0 else cv2.VideoWriter_fourcc(*cc)
        vw = cv2.VideoWriter(path, fourcc, FPS, (WIDTH, HEIGHT))
        if not vw.isOpened():
            vw.release()
            continue
        for i in range(total):
            fr = make_frame(i, total, label)
            if frame_hook:
                fr = frame_hook(fr)
            vw.write(fr)
        vw.release()
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            return cc
    raise RuntimeError(f"No working codec for {path} (tried {fourcc_candidates})")


MP4_CODECS = ['mp4v', 'avc1', 'H264']
AVI_CODECS = ['MJPG', 'XVID', 'mp4v']
LOSSLESS_AVI = ['FFV1', 'HFYU', 0, 'MJPG']   # 0 = uncompressed


# ─── INERT PAYLOADS ───────────────────────────────────────────────────────────

def payload_zip():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('secret_notes.txt',
                   'CyberTriage TEST PAYLOAD - Case 2002-A\nMeeting at dock 7, 23:00.\n' * 5)
        z.writestr('credentials.csv', 'user,password\nalice,test123\nbob,hunter2\n')
    return buf.getvalue()


def payload_pdf():
    return (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]>>endobj\n"
            b"trailer<</Root 1 0 R>>\n%%EOF\n"
            b"% CyberTriage test payload - hidden document\n")


def payload_exe_stub():
    # 'MZ' header + text only. NOT a runnable program.
    return (b"MZ" + b"\x90\x00\x03\x00\x00\x00\x04\x00" + b"\x00" * 50 +
            b"THIS IS A HARMLESS TEST STUB FOR FORENSICS DEMO. NOT EXECUTABLE.\x00" * 3)


def payload_text():
    return (b"CYBERTRIAGE-TEST-PAYLOAD\nThe password is: Tr1age!2002\n"
            b"Exfil target: ftp://example.invalid/drop\n")


def payload_sqlite_stub():
    return b"SQLite format 3\x00" + b"\x00" * 100 + b"test_table|id|name|CyberTriage demo rows\x00" * 4


# ─── EMBEDDING HELPERS ────────────────────────────────────────────────────────

def append_payload(src, dst, payload):
    """Technique 1: bytes appended after the container end."""
    shutil.copyfile(src, dst)
    with open(dst, 'ab') as f:
        f.write(payload)


def add_free_box(src, dst, payload, pad=1024):
    """
    Technique 2: payload hidden in a valid top-level 'free' box at the END of the
    MP4. Container stays well-formed (so NOT flagged as 'appended'), but the magic
    scanner finds it. Placed after moov so stco chunk offsets are untouched.
    Zero padding keeps the signature past the scanner's 512-byte skip window.
    """
    shutil.copyfile(src, dst)
    body = b'\x00' * pad + payload
    with open(dst, 'ab') as f:
        f.write(struct.pack('>I', 8 + len(body)) + b'free' + body)


def tag_mp4(path, tags):
    """Technique 3: abuse iTunes-style metadata atoms via mutagen."""
    from mutagen.mp4 import MP4
    mp = MP4(path)
    for k, v in tags.items():
        mp[k] = [v]
    mp.save()


def lsb_embed_hook(density=0.92):
    """
    Technique 4: force the blue-channel LSB plane to a heavily skewed pattern
    (what a naive LSB embedder of structured/low-entropy data produces).
    app.py's detect_lsb flags ratios outside 0.35-0.65 on >=2 of 5 probe frames.
    """
    def hook(frame):
        bits = (RNG.random(frame.shape[:2]) < density).astype(np.uint8)
        frame[:, :, 0] = (frame[:, :, 0] & 0xFE) | bits
        return frame
    return hook


def measure_lsb(path):
    cap = cv2.VideoCapture(path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    vals = []
    for p in (0.1, 0.25, 0.5, 0.75, 0.9):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(total * p))
        ok, fr = cap.read()
        if ok:
            vals.append(round(float((fr[:, :, 0] & 1).mean()), 3))
    cap.release()
    return vals


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Generate CyberTriage test videos")
    ap.add_argument('-o', '--out', default='test_videos')
    ap.add_argument('--verify', action='store_true',
                    help="import app.py from this folder and run its analyzer on each file")
    args = ap.parse_args()

    out = args.out
    os.makedirs(out, exist_ok=True)
    tmp = os.path.join(out, '_tmp')
    os.makedirs(tmp, exist_ok=True)
    P = lambda n: os.path.join(out, n)

    manifest = []

    def record(name, technique, expected):
        manifest.append({
            'file': name,
            'size_bytes': os.path.getsize(P(name)),
            'technique': technique,
            'expected_findings': expected,
        })
        print(f"  [+] {name:34s} {os.path.getsize(P(name)):>10,} bytes  - {technique}")

    print("Generating base videos ...")
    base_mp4 = os.path.join(tmp, 'base.mp4')
    cc = write_video(base_mp4, 'CyberTriage test video', MP4_CODECS)
    print(f"  MP4 codec used: {cc}")
    base_avi = os.path.join(tmp, 'base.avi')
    cc = write_video(base_avi, 'CyberTriage AVI test', AVI_CODECS)
    print(f"  AVI codec used: {cc}")

    print("\nBuilding test cases ...")

    # 0 - baseline
    shutil.copyfile(base_mp4, P('clean_baseline.mp4'))
    record('clean_baseline.mp4', 'None (control)',
           'No HIGH findings expected. A few MEDIUM/HIGH "signature" hits for short 2-byte '
           'magics (MZ, BM, BZh, 0xFFD8FF...) can still occur by chance in compressed video data.')

    # 1 - appended ZIP (MP4)
    append_payload(base_mp4, P('appended_zip.mp4'), payload_zip())
    record('appended_zip.mp4', 'Appended ZIP after MP4 container',
           'HIGH: Appended Data after MP4 Container (magic 0x504B0304); HIGH: Embedded ZIP Archive')

    # 2 - appended PDF (MP4)
    append_payload(base_mp4, P('appended_pdf.mp4'), payload_pdf())
    record('appended_pdf.mp4', 'Appended PDF after MP4 container',
           'HIGH: Appended Data (0x25504446); HIGH: Embedded PDF Document')

    # 3 - appended fake EXE (MP4)
    append_payload(base_mp4, P('appended_exe_stub.mp4'), payload_exe_stub())
    record('appended_exe_stub.mp4', 'Appended fake PE (MZ) stub',
           'HIGH: Appended Data (0x4D5A); HIGH: Embedded Windows PE/EXE')

    # 4 - appended plain text (unknown magic -> default HIGH)
    append_payload(base_mp4, P('appended_text.mp4'), payload_text())
    record('appended_text.mp4', 'Appended plain-text secret (no magic)',
           'HIGH: Appended Data, magic_hint = None (no signature, defaults to HIGH)')

    # 5 - appended SQLite (MP4)
    append_payload(base_mp4, P('appended_sqlite.mp4'), payload_sqlite_stub())
    record('appended_sqlite.mp4', 'Appended SQLite header stub',
           'HIGH: Appended Data; HIGH: Embedded SQLite Database')

    # 6 - appended ZIP (AVI / RIFF)
    append_payload(base_avi, P('appended_zip.avi'), payload_zip())
    record('appended_zip.avi', 'Appended ZIP after RIFF end (AVI)',
           'HIGH: Appended Data after AVI/RIFF Container; HIGH: Embedded ZIP Archive')

    # 7 - ZIP inside a valid free box (container remains well-formed)
    add_free_box(base_mp4, P('hidden_in_free_box.mp4'), payload_zip())
    record('hidden_in_free_box.mp4', "ZIP hidden inside a valid top-level 'free' atom",
           'HIGH: Embedded ZIP Archive only (NOT flagged as appended - tests signature scanner)')

    # 8 - suspicious metadata
    shutil.copyfile(base_mp4, P('metadata_suspicious.mp4'))
    big_b64 = base64.b64encode(RNG.bytes(900)).decode()
    tag_mp4(P('metadata_suspicious.mp4'), {
        '\xa9cmt': 'hidden message: meet at midnight - secret key follows',
        '\xa9nam': 'Holiday Footage',
        '\xa9too': 'payload-encoder v1.0 (covert channel)',
        '\xa9des': big_b64,
    })
    record('metadata_suspicious.mp4', 'Suspicious keywords + oversized Base64 tag in MP4 atoms',
           'MEDIUM: Suspicious Keyword in Metadata (hidden/secret/payload/covert); '
           'MEDIUM: Anomalously Large Metadata Value (~1200 chars)')

    # 9 - everything at once
    add_free_box(base_mp4, os.path.join(tmp, 'multi_stage1.mp4'), payload_pdf())
    tag_mp4(os.path.join(tmp, 'multi_stage1.mp4'),
            {'\xa9cmt': 'encoded payload inside - do not share',
             '\xa9des': base64.b64encode(RNG.bytes(600)).decode()})
    append_payload(os.path.join(tmp, 'multi_stage1.mp4'), P('multi_technique.mp4'),
                   payload_zip() + payload_exe_stub())
    record('multi_technique.mp4', 'Free-box PDF + metadata abuse + appended ZIP/EXE',
           'Findings from appended, signature AND metadata detectors at once '
           '(good for the report/recovery demo)')

    # 10 - LSB (lossless AVI so the pattern survives decoding)
    print("  ... writing lossless AVI for LSB test (may be large)")
    lsb_path = P('lsb_suspect.avi')
    cc = write_video(lsb_path, 'LSB test (lossless)', LOSSLESS_AVI, frame_hook=lsb_embed_hook())
    ratios = measure_lsb(lsb_path)
    print(f"      codec={cc!r}, measured blue-LSB ratios on probe frames: {ratios}")
    if sum(1 for r in ratios if r < 0.35 or r > 0.65) < 2:
        print("      [!] Codec was lossy - LSB pattern did not survive. Install ffmpeg-enabled "
              "OpenCV or a lossless codec (FFV1/HFYU).")
    record('lsb_suspect.avi', f'Skewed blue-channel LSB plane (codec={cc})',
           'MEDIUM: LSB Steganography Indicator (>=2/5 probe frames outside 0.35-0.65)')

    shutil.rmtree(tmp, ignore_errors=True)

    with open(P('MANIFEST.json'), 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f"\nDone. {len(manifest)} files + MANIFEST.json in '{out}/'")

    # ── optional self-check against the real analyzer ─────────────────────────
    if args.verify:
        print("\n=== VERIFY against app.py ===")
        sys.path.insert(0, os.getcwd())
        try:
            import app as cyber
        except Exception as e:
            print(f"Could not import app.py: {e}")
            return
        for m in manifest:
            fp = P(m['file'])
            meta = cyber.get_video_metadata(fp)
            res = cyber.run_steg_analysis(fp, meta)
            kinds = sorted({f['type'] for f in res['findings'] if f['severity'] in ('HIGH', 'MEDIUM')})
            print(f"\n{m['file']}  counts={res['counts']}")
            for k in kinds:
                print(f"    - {k}")


if __name__ == '__main__':
    main()