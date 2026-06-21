# CyberTriage — Video Forensics Analysis Tool

> **CY-2002/3006 Digital Forensics | Semester Project — Tool #3: Cyber Triage Tool for Video Analysis**

---

## Tool Overview

CyberTriage is a web-based digital forensics tool for comprehensive video evidence analysis. It allows forensic investigators to:

- Ingest video files in multiple formats as digital evidence
- Extract individual frames at user-specified timestamps or regular intervals for quick visual triage
- Play the video directly inside the browser-based interface
- Perform steganography detection (appended data, embedded file signatures, metadata anomalies, LSB analysis)
- Attempt recovery of hidden/embedded media objects
- View detailed video metadata (filesystem, codec, and embedded tag fields)
- Maintain a forensic log of all analysis actions per session

The tool runs **entirely locally** — no data ever leaves the investigator's machine. Built with Python (Flask) on the backend and vanilla HTML/CSS/JS on the frontend.

---

## Features

| Feature | Description |
|---|---|
| 🎬 Multi-Format Video Support | MP4, AVI, MOV, MKV, WMV, FLV, WEBM, MPEG, M4V, 3GP, TS, MTS, M2TS |
| 🖼️ Frame Extraction | Extract frames at specific timestamps (HH:MM:SS or seconds) or at automatic intervals |
| ▶️ Built-In Video Player | Play evidence video directly in the browser — no external software needed |
| 🛡️ Steganography Detection | 5 independent modules: appended data scanner, file signature carver, LSB anomaly detector, metadata anomaly scanner, entropy analyzer |
| 💾 Hidden Data Recovery | Carve and download embedded/appended files detected in the video container |
| 📋 Metadata Extraction | Filesystem timestamps, OpenCV video properties, ffprobe codec info, embedded string scan |
| 📝 Forensic Log | In-session audit trail of all analysis actions with timestamps |

---

## Dependencies and Prerequisites

### System Requirements

| Component | Minimum | Recommended |
|---|---|---|
| OS | Windows 10 / Ubuntu 20.04 / macOS 11 | Ubuntu 22.04 / Windows 11 |
| Python | 3.8 | 3.10+ |
| RAM | 4 GB | 8 GB |
| Disk | 2 GB free | 10 GB free |
| Browser | Chrome 90+ / Firefox 88+ / Edge 90+ | Chrome (latest) |

### Python Packages

```text
flask>=2.3.0
opencv-python-headless>=4.8.0
Pillow>=10.0.0
mutagen>=1.47.0
numpy>=1.24.0
```

All listed in `requirements.txt`.

---

## Installation Instructions

### Step 1 — Clone / Extract the Project

```bash
# Clone from GitHub
git clone https://github.com/musa42069/VideoAnalysisTool.git
cd VideoAnalysisTool

# OR if you received a ZIP
unzip VideoAnalysisTool.zip
cd VideoAnalysisTool
```

### Step 2 — Create a Virtual Environment (Recommended)

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

If you encounter issues with `opencv-python-headless`:
```bash
pip install opencv-python --upgrade
```

**Ubuntu/Debian — if OpenCV fails:**
```bash
sudo apt-get install libgl1-mesa-glx libglib2.0-0
```

---

## Execution Steps

### Start the Server

```bash
python app.py
```

Expected output:

CyberTriage - Video Forensics Analysis Tool

Open your browser at: http://127.0.0.1:5000

### Open the Interface

Navigate to `http://localhost:5000` in Chrome or Firefox.

### Generate Test Videos (Optional but Recommended)

```bash
python generate_test_videos.py
```

Creates three test videos in `test_videos/`:

| File | Duration | Purpose |
|---|---|---|
| `test_scene_changes_60s.mp4` | 60s | 6 scene changes — test manual timestamp extraction |
| `test_forensic_footage_30s.mp4` | 30s | Event-labelled footage — test interval extraction |
| `test_steg_embedded.mp4` | 10s | Hidden payload appended — test steganography detection |

---

## Platform Compatibility

| Platform | Status | Notes |
|---|---|---|
| Windows 10/11 | ✅ Supported | Use `python`, not `python3` |
| Ubuntu 20.04/22.04 | ✅ Supported | May need `libgl1-mesa-glx` for OpenCV |
| macOS 11+ | ✅ Supported | Install Xcode command line tools |
| WSL2 (Windows) | ✅ Supported | Access at `http://localhost:5000` |

---

## Supported Video Formats

| Format | Extension |
|---|---|
| MPEG-4 | `.mp4`, `.m4v` |
| AVI | `.avi` |
| QuickTime | `.mov` |
| Matroska | `.mkv` |
| Windows Media | `.wmv` |
| Flash Video | `.flv` |
| WebM | `.webm` |
| MPEG | `.mpeg`, `.mpg` |
| 3GPP | `.3gp` |
| MPEG-TS | `.ts`, `.mts`, `.m2ts` |

---

## Project Structure

VideoAnalysisTool/

├── app.py                     # Main Flask application & API endpoints

├── requirements.txt           # Python dependencies

├── generate_test_videos.py    # Test video generator

│

├── utils/

│   ├── frame_extractor.py     # Frame extraction engine (OpenCV)

│   ├── steg_detector.py       # Steganography detection pipeline (5 modules)

│   └── metadata_extractor.py  # Metadata extraction (OpenCV + ffprobe)

│

├── templates/

│   └── index.html             # Web interface (HTML + CSS + JS)

│

└── static/

├── uploads/               # Uploaded evidence (auto-created, gitignored)

└── frames/                # Extracted frames (auto-created, gitignored)


---

## Troubleshooting

**Port already in use:**
```bash
# Linux/macOS
lsof -i :5000
kill -9 <PID>

# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```
Then restart with `python app.py`.

**Large video upload fails:**
Open `app.py` and increase `MAX_CONTENT_LENGTH`:
```python
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024 * 1024  # 4 GB
```

**OpenCV cannot open video:**
- Ensure the file is not corrupted
- Try converting: `ffmpeg -i input.mkv output.mp4`
- Verify the format is in the supported list above

**Module not found error:**
Ensure your virtual environment is activated, then:
```bash
pip install -r requirements.txt
```

**Browser video player not working:**
- Use Chrome or Firefox (recommended)
- Frame extraction still works even if in-browser playback fails

---

## Security Notice

This tool is designed for **local forensic use only**. Do not expose port 5000 to the internet. Uploaded evidence files are stored in `static/uploads/` and are never transmitted externally.

---

## Legal and Ethical Notice

This tool must only be used on video evidence for which proper legal authorization has been obtained. Unauthorized analysis of digital evidence may violate applicable laws including Pakistan's Prevention of Electronic Crimes Act (PECA) 2016.

---

*CY-2002/3006 Digital Forensics — Semester Project | April 2026*