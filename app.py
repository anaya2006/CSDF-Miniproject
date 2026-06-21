"""
CyberTriage - Video Forensics Analysis Tool
CY-2002/3006 Digital Forensics Semester Project
"""

import os
import json
import uuid
import struct
import shutil
import hashlib
import mimetypes
import re
from datetime import datetime
from collections import defaultdict
from flask import Flask, render_template, request, jsonify, send_from_directory

import cv2
import mutagen

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024
app.config['UPLOAD_FOLDER']    = 'static/uploads'
app.config['FRAMES_FOLDER']    = 'static/frames'
app.config['RECOVERED_FOLDER'] = 'static/recovered'

ALLOWED_EXTENSIONS = {
    'mp4','avi','mov','mkv','wmv','flv','webm','mpeg','mpg','m4v','3gp','ts','mts'
}
for d in (app.config['UPLOAD_FOLDER'], app.config['FRAMES_FOLDER'], app.config['RECOVERED_FOLDER']):
    os.makedirs(d, exist_ok=True)

# ─── MAGIC SIGNATURE TABLE ────────────────────────────────────────────────────
# (magic_bytes) -> (display_label, extension, severity, context_note)
#
# HIGH   = file type has NO legitimate reason to appear inside a video stream
# MEDIUM = can be legitimate embedded content (thumbnail, cover art) but worth noting
# INFO   = almost always legitimate codec/container internals — only grouped/flagged
#          when count is surprisingly high
#
MAGIC_TABLE = [
    # ── Executables & scripts ──────────────────────────────────────────
    (b'MZ',                  'Windows PE/EXE',     'exe',  'HIGH',
     'Executable code in a video file is a critical forensic indicator.'),
    (b'\x7fELF',             'Linux ELF Binary',   'elf',  'HIGH',
     'Linux executable embedded inside video — critical finding.'),
    # ── Archives ──────────────────────────────────────────────────────
    (b'PK\x03\x04',          'ZIP Archive',         'zip',  'HIGH',
     'ZIP archives have no legitimate place inside a video stream.'),
    (b'Rar!\x1a\x07',        'RAR Archive',         'rar',  'HIGH',
     'RAR archives have no legitimate place inside a video stream.'),
    (b'7z\xbc\xaf\x27\x1c', '7-Zip Archive',       '7z',   'HIGH',
     '7-Zip archives have no legitimate place inside a video stream.'),
    (b'\x1f\x8b',            'GZIP Data',           'gz',   'HIGH',
     'GZIP-compressed data embedded in video is highly suspicious.'),
    (b'BZh',                 'BZIP2 Data',          'bz2',  'HIGH',
     'BZIP2-compressed data embedded in video is highly suspicious.'),
    # ── Documents ─────────────────────────────────────────────────────
    (b'%PDF',                'PDF Document',        'pdf',  'HIGH',
     'PDF documents have no legitimate place inside a video stream.'),
    (b'\xd0\xcf\x11\xe0',   'MS-OLE Document',     'doc',  'HIGH',
     'Legacy MS Office document signature found inside video.'),
    # ── Databases ─────────────────────────────────────────────────────
    (b'SQLite format 3\x00', 'SQLite Database',     'db',   'HIGH',
     'SQLite database hidden in video stream — possible data exfiltration.'),
    # ── Images — medium (could be cover art / thumbnails) ─────────────
    (b'\xff\xd8\xff',        'JPEG Image',          'jpg',  'MEDIUM',
     'JPEG images are common as embedded thumbnails; check context.'),
    (b'\x89PNG\r\n\x1a\n',  'PNG Image',           'png',  'MEDIUM',
     'PNG images can be legitimate cover art; check context.'),
    (b'GIF87a',              'GIF Image',           'gif',  'MEDIUM',
     'GIF image found; could be cover art or hidden content.'),
    (b'GIF89a',              'GIF Image',           'gif',  'MEDIUM',
     'GIF image found; could be cover art or hidden content.'),
    (b'BM',                  'BMP Image',           'bmp',  'MEDIUM',
     'BMP image found inside video container.'),
    # ── Audio — almost always legitimate codec components ──────────────
    (b'ID3',                 'MP3/ID3 Tags',        'mp3',  'INFO',
     'ID3 tags are normal metadata in MP4/MKV audio tracks.'),
    (b'\xff\xfb',            'MP3 Audio Frame',     'mp3',  'INFO',
     'MP3 audio frames are a standard component of video containers.'),
    (b'\xff\xf3',            'MP3 Audio Frame',     'mp3',  'INFO',
     'MP3 audio frames are a standard component of video containers.'),
    (b'\xff\xf2',            'MP3 Audio Frame',     'mp3',  'INFO',
     'MP3 audio frames are a standard component of video containers.'),
    (b'OggS',                'OGG Audio',           'ogg',  'INFO',
     'OGG streams are a normal codec in MKV/WebM containers.'),
    (b'fLaC',                'FLAC Audio',          'flac', 'INFO',
     'FLAC is a legitimate lossless audio codec in MKV.'),
    (b'RIFF',                'RIFF Sub-chunk',      'wav',  'INFO',
     'RIFF sub-chunks appear legitimately inside AVI and MP4.'),
]

# Types that appear naturally and very frequently; suppress unless count is huge
NOISY_LABELS = {
    'MP3/ID3 Tags', 'MP3 Audio Frame', 'OGG Audio', 'FLAC Audio', 'RIFF Sub-chunk'
}
NOISY_THRESHOLD = 20   # more than this many hits → report as grouped anomaly


def allowed_file(fn):
    return '.' in fn and fn.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def file_hash(filepath):
    md5 = hashlib.md5()
    sha = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            md5.update(chunk); sha.update(chunk)
    return md5.hexdigest(), sha.hexdigest()


# ─── METADATA ─────────────────────────────────────────────────────────────────

def get_video_metadata(filepath):
    meta = {}
    cap  = cv2.VideoCapture(filepath)
    if not cap.isOpened():
        return meta

    fc  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    w   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fcc = int(cap.get(cv2.CAP_PROP_FOURCC))
    cap.release()

    try:
        codec = struct.pack('<I', fcc).decode('latin-1').strip('\x00') or 'N/A'
    except Exception:
        codec = 'N/A'

    dur = (fc / fps) if fps > 0 and fc > 0 else 0
    meta.update({
        'frame_count':        fc,
        'fps':                round(fps, 4),
        'width':              w,
        'height':             h,
        'codec':              codec,
        'duration_seconds':   round(dur, 3),
        'duration_formatted': str(datetime.utcfromtimestamp(dur).strftime('%H:%M:%S')),
    })

    stat = os.stat(filepath)
    meta.update({
        'file_size':    stat.st_size,
        'file_size_mb': round(stat.st_size / (1024*1024), 3),
        'created':      datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
        'modified':     datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
        'mime_type':    mimetypes.guess_type(filepath)[0] or 'unknown',
        'extension':    filepath.rsplit('.', 1)[-1].lower(),
    })

    # ── Mutagen tags + audio info ──────────────────────────────────────────────
    tags_dict  = {}
    audio_info = {}
    try:
        mf = mutagen.File(filepath, easy=False)
        if mf:
            info = mf.info
            for attr in ('bitrate','sample_rate','channels','length','mode',
                         'codec','codec_description','video_resolution',
                         'video_codec','audio_codec','sketchy','bitratemode'):
                if hasattr(info, attr):
                    v = getattr(info, attr)
                    if v is not None:
                        audio_info[attr] = str(v)

            if mf.tags:
                if hasattr(mf.tags, 'items'):
                    for k, v in mf.tags.items():
                        sv = str(v)
                        if sv.startswith('[') and sv.endswith(']'):
                            sv = sv[1:-1]
                        tags_dict[str(k)] = sv[:600]
                elif hasattr(mf.tags, 'values'):
                    for frame in mf.tags.values():
                        try:
                            tags_dict[frame.FrameID] = str(frame)[:600]
                        except Exception:
                            pass
    except Exception:
        pass

    meta['mutagen_tags']  = tags_dict
    meta['mutagen_extra'] = audio_info

    # ── XMP + raw printable strings from first 256 KB ─────────────────────────
    raw_strings = {}
    try:
        with open(filepath, 'rb') as f:
            header = f.read(262144)

        xmp_s = header.find(b'<?xpacket begin')
        if xmp_s != -1:
            xmp_e = header.find(b'</x:xmpmeta>', xmp_s)
            if xmp_e != -1:
                xmp_blob = header[xmp_s: xmp_e+12].decode('utf-8', errors='replace')
                for m in re.finditer(r'(\w+:\w+)="([^"]{1,300})"', xmp_blob):
                    raw_strings['XMP:' + m.group(1)] = m.group(2)

        printable = re.compile(rb'[\x20-\x7e]{12,256}')
        seen_vals = set()
        for m in printable.finditer(header):
            s = m.group().decode('latin-1')
            sl = s.lower()
            if s in seen_vals:
                continue
            if any(kw in sl for kw in ('encoder','creator','comment','description',
                                        'copyright','title','artist','album','date',
                                        'location','gps','software','handler',
                                        'major_brand','compatible_brands','tool',
                                        'creation_time','language')):
                seen_vals.add(s)
                raw_strings[f'RawStr@{m.start():#010x}'] = s[:250]
    except Exception:
        pass

    meta['raw_strings'] = raw_strings
    meta['md5'], meta['sha256'] = file_hash(filepath)
    return meta


# ─── FRAME EXTRACTION ─────────────────────────────────────────────────────────

def extract_frames(filepath, timestamps, session_id):
    cap = cv2.VideoCapture(filepath)
    if not cap.isOpened():
        return []
    fps   = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    dur   = total / fps if fps > 0 else 0
    fdir  = os.path.join(app.config['FRAMES_FOLDER'], session_id)
    os.makedirs(fdir, exist_ok=True)
    frames = []
    for ts in timestamps:
        ts = float(ts)
        if not (0 <= ts <= dur):
            continue
        fn = int(ts * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, fn)
        ret, frame = cap.read()
        if not ret:
            continue
        ts_str = datetime.utcfromtimestamp(ts).strftime('%H_%M_%S')
        fname  = f"frame_{ts_str}_{int(ts*1000)}.jpg"
        cv2.imwrite(os.path.join(fdir, fname), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        frames.append({
            'filename':            fname,
            'url':                 f'/static/frames/{session_id}/{fname}',
            'timestamp':           ts,
            'timestamp_formatted': datetime.utcfromtimestamp(ts).strftime('%H:%M:%S'),
            'frame_number':        fn,
            'width':               frame.shape[1],
            'height':              frame.shape[0],
        })
    cap.release()
    return frames


def extract_frames_interval(filepath, interval, session_id):
    cap = cv2.VideoCapture(filepath)
    if not cap.isOpened():
        return []
    fps  = cap.get(cv2.CAP_PROP_FPS)
    tot  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    dur  = tot / fps if fps > 0 else 0
    cap.release()
    ts, timestamps = 0.0, []
    while ts <= dur:
        timestamps.append(ts)
        ts += interval
    return extract_frames(filepath, timestamps, session_id)


# ─── STEGANOGRAPHY ────────────────────────────────────────────────────────────

def _appended_severity(data, offset):
    chunk = data[offset:offset+16]
    for magic, label, ext, sev, _ in MAGIC_TABLE:
        if chunk.startswith(magic):
            return sev, '0x' + magic.hex().upper()
    return 'HIGH', None


def detect_appended_data(filepath, data):
    findings = []
    ext       = filepath.rsplit('.', 1)[-1].lower()
    file_size = len(data)
    try:
        if ext in ('mp4', 'mov', 'm4v'):
            offset, last_valid = 0, 0
            while offset < len(data) - 8:
                try:
                    sz = struct.unpack('>I', data[offset:offset+4])[0]
                    if sz == 0:
                        last_valid = len(data); break
                    if sz < 8:
                        break
                    last_valid = offset + sz
                    offset    += sz
                except Exception:
                    break
            if 0 < last_valid < file_size - 16:
                appended   = file_size - last_valid
                sev, magic = _appended_severity(data, last_valid)
                findings.append({
                    'category':     'container_anomaly',
                    'type':         'Appended Data after MP4 Container',
                    'description':  (f'{appended:,} bytes of data exist after the valid MP4 container '
                                     f'end (offset 0x{last_valid:X}). This is a classic steganography carrier technique.'),
                    'offset':       last_valid,
                    'size':         appended,
                    'severity':     sev,
                    'recoverable':  True,
                    'data_preview': data[last_valid:last_valid+32].hex(),
                    'context':      'The MP4 player stops at the container end — data after it is invisible during normal playback.',
                    'magic_hint':   magic,
                    'extension':    'bin',
                })

        elif ext == 'avi':
            if data[:4] == b'RIFF':
                riff_end = struct.unpack('<I', data[4:8])[0] + 8
                if riff_end < file_size - 16:
                    appended   = file_size - riff_end
                    sev, magic = _appended_severity(data, riff_end)
                    findings.append({
                        'category':     'container_anomaly',
                        'type':         'Appended Data after AVI/RIFF Container',
                        'description':  (f'{appended:,} bytes appended beyond RIFF-declared size '
                                         f'(RIFF end: 0x{riff_end:X}, file end: 0x{file_size:X}).'),
                        'offset':       riff_end,
                        'size':         appended,
                        'severity':     sev,
                        'recoverable':  True,
                        'data_preview': data[riff_end:riff_end+32].hex(),
                        'context':      'Appending data after RIFF end is invisible to standard media players.',
                        'magic_hint':   magic,
                        'extension':    'bin',
                    })
    except Exception as e:
        findings.append({'category':'error','type':'Container Analysis Error',
                         'description':str(e),'severity':'INFO','recoverable':False,'context':''})
    return findings


def detect_embedded_files(filepath, data):
    """
    Scan for magic byte signatures with smart deduplication and severity.
    Results are grouped per label type to avoid hundreds of duplicate findings.
    """
    ext = filepath.rsplit('.', 1)[-1].lower()

    # Accumulate all hits per label
    hits_by_label = defaultdict(list)  # label -> list of {offset, magic, ext, sev, note}
    for magic, label, file_ext, severity, note in MAGIC_TABLE:
        skip  = 4096 if len(magic) <= 2 else 512
        start = skip
        while True:
            idx = data.find(magic, start)
            if idx == -1:
                break
            hits_by_label[label].append({
                'offset':    idx,
                'magic':     '0x' + magic.hex().upper(),
                'extension': file_ext,
                'severity':  severity,
                'note':      note,
                'label':     label,
            })
            start = idx + 1

    findings = []
    for label, hits in hits_by_label.items():
        count    = len(hits)
        severity = hits[0]['severity']
        note     = hits[0]['note']
        file_ext = hits[0]['extension']
        magic_h  = hits[0]['magic']
        offsets  = [h['offset'] for h in hits]

        # ── Noisy/common types: suppress small counts entirely, group large ones ──
        if label in NOISY_LABELS:
            if count <= NOISY_THRESHOLD:
                continue   # completely normal — skip
            findings.append({
                'category':    'signature_grouped',
                'type':        f'Abnormal Count: {label}',
                'description': (f'{count} occurrences of {label} ({magic_h}) found '
                                f'throughout the file. Normal for audio tracks is ≤20; '
                                f'this high count may indicate frame-level data embedding.'),
                'file_type':   label,
                'extension':   file_ext,
                'severity':    'MEDIUM',
                'count':       count,
                'offsets':     offsets[:5],
                'offset':      offsets[0],
                'context':     note,
                'recoverable': False,
                'magic_hex':   magic_h,
            })
            continue

        # ── For non-noisy types: one finding per type, listing all offsets ──────
        if count == 1:
            desc = (f'{label} signature ({magic_h}) found at offset '
                    f'0x{offsets[0]:X} ({offsets[0]:,} bytes into file).')
        else:
            first5 = ', '.join(f'0x{o:X}' for o in offsets[:5])
            more   = f' (+{count-5} more)' if count > 5 else ''
            desc   = (f'{count} {label} signatures ({magic_h}) detected at: '
                      f'{first5}{more}.')

        findings.append({
            'category':    'embedded_signature',
            'type':        f'Embedded {label}',
            'description': desc,
            'file_type':   label,
            'extension':   file_ext,
            'severity':    severity,
            'count':       count,
            'offsets':     offsets[:10],
            'offset':      offsets[0],
            'context':     note,
            'recoverable': severity in ('HIGH','MEDIUM') and count <= 5,
            'magic_hex':   magic_h,
        })

    return findings


def detect_metadata_steg(metadata):
    SUSPICIOUS = ['hidden','secret','steg','base64','encoded','payload',
                  'cipher','encrypt','covert','embed','exfil']
    findings = []
    seen     = set()
    all_tags = {**metadata.get('mutagen_tags', {}), **metadata.get('raw_strings', {})}

    for key, val in all_tags.items():
        sv  = str(val)
        slv = sv.lower()
        for kw in SUSPICIOUS:
            if kw in slv and key not in seen:
                seen.add(key)
                findings.append({
                    'category':    'metadata_anomaly',
                    'type':        'Suspicious Keyword in Metadata',
                    'description': f'Tag "{key}" contains suspicious keyword "{kw}".',
                    'severity':    'MEDIUM',
                    'recoverable': False,
                    'tag_key':     key,
                    'tag_value':   sv[:300],
                    'context':     'Metadata fields are sometimes abused to carry encoded payloads.',
                })
                break

        if len(sv) > 300 and key not in seen:
            seen.add(key)
            findings.append({
                'category':    'metadata_anomaly',
                'type':        'Anomalously Large Metadata Value',
                'description': (f'Tag "{key}" is unusually large ({len(sv):,} chars). '
                                f'Possible Base64/hex-encoded payload.'),
                'severity':    'MEDIUM',
                'recoverable': False,
                'tag_key':     key,
                'tag_value':   sv[:400] + ('…' if len(sv) > 400 else ''),
                'context':     'Encoded payloads are often hidden in oversized metadata fields.',
            })
    return findings


def detect_lsb(filepath):
    findings = []
    try:
        import numpy as np
        cap = cv2.VideoCapture(filepath)
        if not cap.isOpened():
            return findings
        total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        probes = [int(total * p) for p in (0.1, 0.25, 0.5, 0.75, 0.9) if int(total*p) < total]
        anomalous = []
        for fn in probes:
            cap.set(cv2.CAP_PROP_POS_FRAMES, fn)
            ret, frame = cap.read()
            if not ret:
                continue
            ratio = (frame[:, :, 0] & 1).mean()
            if ratio < 0.35 or ratio > 0.65:
                anomalous.append((fn, round(ratio, 3)))
        cap.release()
        if len(anomalous) >= 2:
            findings.append({
                'category':    'lsb_analysis',
                'type':        'LSB Steganography Indicator',
                'description': (f'LSB plane deviates from expected ~0.5 in '
                                f'{len(anomalous)}/{len(probes)} sampled frames. '
                                f'Details: {anomalous}'),
                'severity':    'MEDIUM',
                'recoverable': False,
                'context':     'LSB steganography replaces pixel LSBs with payload data, skewing the natural 50% distribution.',
            })
    except Exception as e:
        findings.append({'category':'error','type':'LSB Analysis Error',
                         'description':str(e),'severity':'INFO','recoverable':False,'context':''})
    return findings


def run_steg_analysis(filepath, metadata):
    with open(filepath, 'rb') as f:
        data = f.read()

    findings = []
    findings += detect_appended_data(filepath, data)
    findings += detect_embedded_files(filepath, data)
    findings += detect_metadata_steg(metadata)
    findings += detect_lsb(filepath)

    order = {'HIGH': 0, 'MEDIUM': 1, 'INFO': 2}
    findings.sort(key=lambda x: (order.get(x.get('severity','INFO'), 2),
                                  x.get('category',''), x.get('type','')))
    counts = {'HIGH': 0, 'MEDIUM': 0, 'INFO': 0}
    for f in findings:
        counts[f.get('severity','INFO')] += 1

    return {'findings': findings, 'counts': counts, 'total': len(findings)}


# ─── RECOVERY ─────────────────────────────────────────────────────────────────

def recover_hidden(filepath, finding, session_id):
    rec_dir = os.path.join(app.config['RECOVERED_FOLDER'], session_id)
    os.makedirs(rec_dir, exist_ok=True)
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
        offset = finding.get('offset', 0)
        size   = finding.get('size', None)
        ext    = finding.get('extension', 'bin')
        fname  = f"recovered_{uuid.uuid4().hex[:8]}.{ext}"
        chunk  = data[offset: offset + size] if size else data[offset:]
        with open(os.path.join(rec_dir, fname), 'wb') as f:
            f.write(chunk)
        return {'success': True, 'filename': fname,
                'url': f'/static/recovered/{session_id}/{fname}',
                'size': len(chunk), 'extension': ext}
    except Exception as e:
        return {'success': False, 'error': str(e)}


# ─── ROUTES ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file'}), 400
    file = request.files['video']
    if not file.filename or not allowed_file(file.filename):
        return jsonify({'error': f'Unsupported format. Allowed: {", ".join(sorted(ALLOWED_EXTENSIONS))}'}), 400
    session_id = uuid.uuid4().hex
    ext        = file.filename.rsplit('.', 1)[1].lower()
    filename   = f"{session_id}.{ext}"
    filepath   = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    metadata   = get_video_metadata(filepath)
    return jsonify({'success': True, 'session_id': session_id, 'filename': filename,
                    'original_name': file.filename, 'video_url': f'/static/uploads/{filename}',
                    'metadata': metadata})


@app.route('/extract_frames', methods=['POST'])
def extract_frames_route():
    d = request.json
    session_id, filename, mode = d.get('session_id'), d.get('filename'), d.get('mode','timestamps')
    if not session_id or not filename:
        return jsonify({'error': 'Missing params'}), 400
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    fdir = os.path.join(app.config['FRAMES_FOLDER'], session_id)
    if os.path.exists(fdir):
        shutil.rmtree(fdir)
    if mode == 'interval':
        frames = extract_frames_interval(filepath, float(d.get('interval', 10)), session_id)
    else:
        ts = d.get('timestamps', [])
        if not ts:
            return jsonify({'error': 'No timestamps'}), 400
        frames = extract_frames(filepath, ts, session_id)
    return jsonify({'success': True, 'frames': frames, 'count': len(frames)})


@app.route('/analyze_steg', methods=['POST'])
def analyze_steg():
    d = request.json
    session_id, filename = d.get('session_id'), d.get('filename')
    if not session_id or not filename:
        return jsonify({'error': 'Missing params'}), 400
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    metadata = get_video_metadata(filepath)
    result   = run_steg_analysis(filepath, metadata)
    return jsonify({'success': True, **result})


@app.route('/recover', methods=['POST'])
def recover():
    d = request.json
    session_id, filename, finding = d.get('session_id'), d.get('filename'), d.get('finding')
    if not all([session_id, filename, finding]):
        return jsonify({'error': 'Missing params'}), 400
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    return jsonify(recover_hidden(filepath, finding, session_id))


@app.route('/generate_report', methods=['POST'])
def generate_report():
    d = request.json
    sid = d.get('session_id')
    report = {
        'report_id':              uuid.uuid4().hex[:12].upper(),
        'generated_at':           datetime.utcnow().isoformat() + 'Z',
        'case_number':            d.get('case_number','N/A'),
        'investigator':           d.get('investigator','Unknown'),
        'notes':                  d.get('notes',''),
        'evidence':               {'original_filename': d.get('original_name',''), 'session_id': sid, 'metadata': d.get('metadata',{})},
        'frames_extracted':       d.get('frames',[]),
        'steganography_findings': d.get('steg_findings',[]),
        'recovered_files':        d.get('recovered_files',[]),
        'summary': {
            'total_frames':    len(d.get('frames',[])),
            'steg_total':      len(d.get('steg_findings',[])),
            'steg_high':       sum(1 for f in d.get('steg_findings',[]) if f.get('severity')=='HIGH'),
            'steg_medium':     sum(1 for f in d.get('steg_findings',[]) if f.get('severity')=='MEDIUM'),
            'recovered_count': len(d.get('recovered_files',[])),
        },
        'chain_of_custody': {
            'md5':    d.get('metadata',{}).get('md5','N/A'),
            'sha256': d.get('metadata',{}).get('sha256','N/A'),
            'analysis_timestamp': datetime.utcnow().isoformat() + 'Z',
        },
    }
    rec_dir = os.path.join(app.config['RECOVERED_FOLDER'], sid)
    os.makedirs(rec_dir, exist_ok=True)
    with open(os.path.join(rec_dir, 'forensic_report.json'), 'w') as f:
        json.dump(report, f, indent=2)
    return jsonify({'success': True, 'report': report,
                    'report_url': f'/static/recovered/{sid}/forensic_report.json'})


@app.route('/static/uploads/<filename>')
def serve_video(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/static/frames/<sid>/<filename>')
def serve_frame(sid, filename):
    return send_from_directory(os.path.join(app.config['FRAMES_FOLDER'], sid), filename)

@app.route('/static/recovered/<sid>/<filename>')
def serve_recovered(sid, filename):
    return send_from_directory(os.path.join(app.config['RECOVERED_FOLDER'], sid), filename)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)