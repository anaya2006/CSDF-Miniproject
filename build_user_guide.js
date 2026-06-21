const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
  VerticalAlign, PageNumber, Header, Footer, LevelFormat, PageBreak
} = require('docx');
const fs = require('fs');

const ACCENT = "1F4E79";
const LIGHT_BLUE = "D6E4F0";
const DANGER_RED = "C00000";
const WARN_YELLOW = "FFC000";
const GREEN = "375623";
const LIGHT_GRAY = "F2F2F2";
const BORDER_COLOR = "B8CCE4";

const border = { style: BorderStyle.SINGLE, size: 1, color: BORDER_COLOR };
const borders = { top: border, bottom: border, left: border, right: border };
const noBorder = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    children: [new TextRun({ text, bold: true, size: 32, color: ACCENT, font: "Arial" })],
    spacing: { before: 360, after: 200 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: ACCENT, space: 1 } }
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    children: [new TextRun({ text, bold: true, size: 26, color: ACCENT, font: "Arial" })],
    spacing: { before: 280, after: 160 }
  });
}

function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    children: [new TextRun({ text, bold: true, size: 22, color: "2E5090", font: "Arial" })],
    spacing: { before: 200, after: 120 }
  });
}

function p(text, opts = {}) {
  return new Paragraph({
    children: [new TextRun({ text, size: 22, font: "Arial", ...opts })],
    spacing: { before: 80, after: 120 }
  });
}

function bullet(text, level = 0, bold = false) {
  return new Paragraph({
    numbering: { reference: "bullets", level },
    children: [new TextRun({ text, size: 22, font: "Arial", bold })],
    spacing: { before: 60, after: 60 }
  });
}

function numbered(text, level = 0) {
  return new Paragraph({
    numbering: { reference: "numbers", level },
    children: [new TextRun({ text, size: 22, font: "Arial" })],
    spacing: { before: 80, after: 80 }
  });
}

function code(text) {
  return new Paragraph({
    children: [new TextRun({ text, size: 18, font: "Courier New", color: "1F4E79" })],
    spacing: { before: 60, after: 60 },
    shading: { fill: "EEF4FA", type: ShadingType.CLEAR },
    indent: { left: 360 }
  });
}

function pageBreak() {
  return new Paragraph({ children: [new PageBreak()] });
}

function infoBox(label, text, color = LIGHT_BLUE) {
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [9360],
    rows: [new TableRow({
      children: [new TableCell({
        borders,
        width: { size: 9360, type: WidthType.DXA },
        shading: { fill: color, type: ShadingType.CLEAR },
        margins: { top: 120, bottom: 120, left: 200, right: 200 },
        children: [
          new Paragraph({
            children: [new TextRun({ text: label, bold: true, size: 20, font: "Arial", color: ACCENT })],
            spacing: { before: 40, after: 60 }
          }),
          new Paragraph({
            children: [new TextRun({ text, size: 20, font: "Arial" })],
            spacing: { before: 0, after: 40 }
          })
        ]
      })]
    })]
  });
}

function twoColTable(rows, header1, header2) {
  const headerRow = new TableRow({
    children: [
      new TableCell({
        borders, width: { size: 3600, type: WidthType.DXA },
        shading: { fill: ACCENT, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [new Paragraph({ children: [new TextRun({ text: header1, bold: true, color: "FFFFFF", size: 20, font: "Arial" })] })]
      }),
      new TableCell({
        borders, width: { size: 5760, type: WidthType.DXA },
        shading: { fill: ACCENT, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [new Paragraph({ children: [new TextRun({ text: header2, bold: true, color: "FFFFFF", size: 20, font: "Arial" })] })]
      })
    ]
  });

  const dataRows = rows.map(([k, v], i) => new TableRow({
    children: [
      new TableCell({
        borders, width: { size: 3600, type: WidthType.DXA },
        shading: { fill: i % 2 === 0 ? "FFFFFF" : LIGHT_GRAY, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [new Paragraph({ children: [new TextRun({ text: k, bold: true, size: 20, font: "Arial" })] })]
      }),
      new TableCell({
        borders, width: { size: 5760, type: WidthType.DXA },
        shading: { fill: i % 2 === 0 ? "FFFFFF" : LIGHT_GRAY, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [new Paragraph({ children: [new TextRun({ text: v, size: 20, font: "Arial" })] })]
      })
    ]
  }));

  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [3600, 5760],
    rows: [headerRow, ...dataRows]
  });
}

function rubricTable(rows) {
  const headerRow = new TableRow({
    children: [
      new TableCell({
        borders, width: { size: 4000, type: WidthType.DXA },
        shading: { fill: ACCENT, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [new Paragraph({ children: [new TextRun({ text: "Criteria", bold: true, color: "FFFFFF", size: 20, font: "Arial" })] })]
      }),
      new TableCell({
        borders, width: { size: 1000, type: WidthType.DXA },
        shading: { fill: ACCENT, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [new Paragraph({ children: [new TextRun({ text: "Marks", bold: true, color: "FFFFFF", size: 20, font: "Arial" })] })]
      }),
      new TableCell({
        borders, width: { size: 1200, type: WidthType.DXA },
        shading: { fill: ACCENT, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [new Paragraph({ children: [new TextRun({ text: "CLO", bold: true, color: "FFFFFF", size: 20, font: "Arial" })] })]
      }),
      new TableCell({
        borders, width: { size: 3160, type: WidthType.DXA },
        shading: { fill: ACCENT, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [new Paragraph({ children: [new TextRun({ text: "How We Meet It", bold: true, color: "FFFFFF", size: 20, font: "Arial" })] })]
      })
    ]
  });

  const dataRows = rows.map(([c, m, clo, desc], i) => new TableRow({
    children: [
      new TableCell({
        borders, width: { size: 4000, type: WidthType.DXA },
        shading: { fill: i % 2 === 0 ? "FFFFFF" : LIGHT_GRAY, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [new Paragraph({ children: [new TextRun({ text: c, size: 20, font: "Arial" })] })]
      }),
      new TableCell({
        borders, width: { size: 1000, type: WidthType.DXA },
        shading: { fill: i % 2 === 0 ? "FFFFFF" : LIGHT_GRAY, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [new Paragraph({ children: [new TextRun({ text: m, bold: true, color: ACCENT, size: 20, font: "Arial" })] })]
      }),
      new TableCell({
        borders, width: { size: 1200, type: WidthType.DXA },
        shading: { fill: i % 2 === 0 ? "FFFFFF" : LIGHT_GRAY, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [new Paragraph({ children: [new TextRun({ text: clo, size: 20, font: "Arial" })] })]
      }),
      new TableCell({
        borders, width: { size: 3160, type: WidthType.DXA },
        shading: { fill: i % 2 === 0 ? "FFFFFF" : LIGHT_GRAY, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [new Paragraph({ children: [new TextRun({ text: desc, size: 20, font: "Arial" })] })]
      })
    ]
  }));

  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [4000, 1000, 1200, 3160],
    rows: [headerRow, ...dataRows]
  });
}

// ─── DOCUMENT ────────────────────────────────────────────────────────────────
const doc = new Document({
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [
          { level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
          { level: 1, format: LevelFormat.BULLET, text: "\u25CB", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 1080, hanging: 360 } } } }
        ]
      },
      {
        reference: "numbers",
        levels: [
          { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
          { level: 1, format: LevelFormat.LOWER_LETTER, text: "%2.", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 1080, hanging: 360 } } } }
        ]
      }
    ]
  },
  styles: {
    default: {
      document: { run: { font: "Arial", size: 22 } }
    },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial", color: ACCENT },
        paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial", color: ACCENT },
        paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, font: "Arial", color: "2E5090" },
        paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 2 } }
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          children: [
            new TextRun({ text: "CyberTriage — Video Forensics Analysis Tool", size: 18, font: "Arial", color: ACCENT }),
            new TextRun({ text: "    |    CY-2002/3006 Digital Forensics", size: 18, font: "Arial", color: "888888" })
          ],
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: ACCENT, space: 1 } },
          spacing: { after: 0 }
        })]
      })
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          children: [
            new TextRun({ text: "User Guide — Confidential Forensic Document    |    Page ", size: 18, font: "Arial", color: "888888" }),
            new TextRun({ children: [PageNumber.CURRENT], size: 18, font: "Arial", color: ACCENT }),
            new TextRun({ text: " of ", size: 18, font: "Arial", color: "888888" }),
            new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 18, font: "Arial", color: ACCENT })
          ],
          alignment: AlignmentType.CENTER,
          border: { top: { style: BorderStyle.SINGLE, size: 4, color: ACCENT, space: 1 } }
        })]
      })
    },
    children: [

      // ── TITLE PAGE ──────────────────────────────────────────────────────────
      new Paragraph({
        children: [new TextRun({ text: "CyberTriage", size: 72, bold: true, font: "Arial", color: ACCENT })],
        alignment: AlignmentType.CENTER, spacing: { before: 1440, after: 200 }
      }),
      new Paragraph({
        children: [new TextRun({ text: "Video Forensics Analysis Tool", size: 36, font: "Arial", color: "444444" })],
        alignment: AlignmentType.CENTER, spacing: { before: 0, after: 160 }
      }),
      new Paragraph({
        children: [new TextRun({ text: "User Guide", size: 28, bold: true, font: "Arial", color: "666666" })],
        alignment: AlignmentType.CENTER, spacing: { before: 0, after: 800 }
      }),
      new Paragraph({
        children: [new TextRun({ text: "CY-2002/3006 Digital Forensics | Semester Project", size: 22, font: "Arial", color: "888888" })],
        alignment: AlignmentType.CENTER, spacing: { before: 0, after: 120 }
      }),
      new Paragraph({
        children: [new TextRun({ text: "Tool #3 — Cyber Triage Tool for Video Analysis", size: 22, font: "Arial", color: "888888" })],
        alignment: AlignmentType.CENTER, spacing: { before: 0, after: 120 }
      }),
      new Paragraph({
        children: [new TextRun({ text: "Submission: 26 April 2026", size: 22, font: "Arial", color: "888888" })],
        alignment: AlignmentType.CENTER, spacing: { before: 0, after: 2000 }
      }),
      pageBreak(),

      // ── SECTION 1: INTRODUCTION ─────────────────────────────────────────────
      h1("1. Introduction to CyberTriage and Its Forensic Domain"),
      p("CyberTriage is a browser-based digital forensics tool purpose-built for the triage and analysis of video evidence. In modern digital forensic investigations, video files represent a growing and critical source of evidence — from CCTV footage to dashcam recordings, from mobile phone captures to deepfake detection. Investigators need fast, reliable tools to quickly review video content and detect attempts to conceal information within video files."),
      p("CyberTriage addresses this need by providing an integrated environment where a forensic examiner can:"),
      bullet("Upload video evidence in any common format (MP4, AVI, MOV, MKV, WMV, FLV, WebM, MPEG, 3GP, MPEG-TS)"),
      bullet("Extract high-quality JPEG snapshots at user-defined timestamps or at regular intervals, enabling rapid visual review without scrubbing through hours of footage"),
      bullet("Play the video directly within the browser interface with full playback controls (seek, speed, volume)"),
      bullet("Run multi-layer steganography detection: appended data analysis, embedded file signature scanning, metadata anomaly detection, and Least Significant Bit (LSB) statistical analysis"),
      bullet("Recover hidden files or payloads embedded in video containers"),
      bullet("Inspect all embedded metadata fields and compute cryptographic hashes (MD5 and SHA-256) for chain of custody"),
      bullet("Generate structured JSON forensic reports documenting all findings, case information, and evidence integrity"),
      p(""),
      h2("1.1 Forensic Domain: Video Evidence and Steganography"),
      p("The forensic domain covered by CyberTriage spans two primary areas of digital forensics:"),
      h3("Video Triage"),
      p("Video triage refers to the rapid review of video evidence to identify key moments without manual playback of the entire file. In time-sensitive investigations, investigators need to snapshot specific timestamps, review footage at-a-glance across multiple frames, and share visual summaries. CyberTriage automates this process, allowing frame extraction in seconds."),
      h3("Video Steganography Detection"),
      p("Steganography is the practice of hiding information within an ordinary-looking carrier file. Video files are a popular carrier because of their large size and binary complexity. Common techniques include:"),
      bullet("Appending hidden files after the valid container end (the video plays normally but bytes exist beyond the container boundary)"),
      bullet("Embedding file payloads within metadata tags (e.g. unusually large EXIF/ID3 fields)"),
      bullet("Hiding data using Least Significant Bit (LSB) manipulation in pixel values across video frames"),
      bullet("Concealing files by inserting them at offsets matching known magic byte signatures"),
      p("CyberTriage detects all of these techniques and, where possible, offers automated recovery of the hidden content."),

      pageBreak(),

      // ── SECTION 2: LEGAL & ETHICAL CONSIDERATIONS ──────────────────────────
      h1("2. Legal and Ethical Considerations"),
      infoBox(
        "CLO 1 Coverage",
        "This section directly addresses CLO 1: Develop knowledge about forensic laws, standards, regulations, and ethical values. It covers data privacy, evidence handling standards, and admissibility concepts."
      ),
      p(""),
      h2("2.1 Applicable Laws and Standards"),
      p("Digital forensic investigators must operate within applicable legal frameworks. The following laws and standards are relevant when using CyberTriage:"),
      twoColTable([
        ["PECB ISO/IEC 27037", "Guidelines for the identification, collection, acquisition, and preservation of digital evidence."],
        ["Pakistan PECA 2016", "Prevention of Electronic Crimes Act — governs lawful interception and evidence handling in Pakistan."],
        ["Pakistani Evidence Act 1984", "Provides rules on admissibility of documentary and electronic evidence in Pakistani courts."],
        ["NIST SP 800-86", "Guide to Integrating Forensic Techniques into Incident Response — best practices for digital forensics."],
        ["ACPO Good Practice Guide", "UK Association of Chief Police Officers guidelines for computer-based electronic evidence (widely adopted internationally)."],
        ["RFC 3227", "Guidelines for Evidence Collection and Archiving — order of volatility and chain of custody requirements."]
      ], "Law / Standard", "Relevance"),
      p(""),
      h2("2.2 Chain of Custody"),
      p("Chain of custody is the chronological documentation proving the collection, handling, and analysis of evidence. CyberTriage enforces chain of custody through:"),
      bullet("Automatic computation of MD5 and SHA-256 hashes upon evidence upload — these values should match the hash of the original evidence file and be documented in the case notes"),
      bullet("Timestamped forensic reports that record the exact date and time of analysis (in UTC)"),
      bullet("Non-destructive analysis — the original uploaded file is never modified; all frame extraction and steganography analysis reads the file without alteration"),
      bullet("Session IDs that uniquely identify each analysis session, allowing reconstruction of the investigative steps"),
      p(""),
      h2("2.3 Data Privacy and Evidence Handling"),
      p("Investigators must ensure that video evidence is handled in compliance with data privacy laws:"),
      bullet("Video evidence may contain personally identifiable information (PII) such as faces, vehicle plates, or private conversations. Access to this evidence must be restricted to authorized personnel only."),
      bullet("CyberTriage operates entirely locally — no data is transmitted to external servers. All files remain on the investigator's workstation."),
      bullet("Investigators should work on forensic copies (not originals). Use tools such as dcfldd or dd to create verified copies before uploading to CyberTriage."),
      bullet("Recovered hidden files may themselves contain sensitive material. These should be treated as evidence and handled accordingly."),
      bullet("After analysis, if evidence files are no longer needed on the workstation, they should be securely deleted using a certified secure deletion tool (not standard OS deletion)."),
      p(""),
      h2("2.4 Ethical Responsibilities"),
      p("The ethical obligations of a forensic investigator using CyberTriage include:"),
      bullet("Objectivity: Present findings as they are, without bias. The steganography analysis reports findings; the investigator must not overstate or suppress them."),
      bullet("Competence: Do not conduct forensic analysis beyond your training. If findings are unclear, consult a senior examiner."),
      bullet("Non-interference: Do not access or analyze evidence without proper authorization (warrant, written consent, or legal authority)."),
      bullet("Reporting accuracy: The generated JSON report is a forensic artifact — its contents must be accurate and must not be altered after generation."),
      bullet("Whistleblowing: If during analysis you discover evidence of a crime not covered by your original mandate, follow your organization's disclosure procedures."),
      p(""),
      infoBox("Note on Admissibility",
        "Evidence processed through CyberTriage is admissible only if: (1) the original file hash matches the hash recorded at intake, (2) the analyst can testify about the tool's methodology, and (3) the chain of custody has been maintained without interruption. Always document your analysis steps in detail.",
        "FFF2CC"
      ),

      pageBreak(),

      // ── SECTION 3: SYSTEM REQUIREMENTS ─────────────────────────────────────
      h1("3. System Requirements"),
      h2("3.1 Hardware Requirements"),
      twoColTable([
        ["Processor", "Intel Core i3 / AMD Ryzen 3 (minimum); i5/Ryzen 5 recommended for 4K video"],
        ["RAM", "4 GB minimum; 8 GB recommended for large video files"],
        ["Disk Space", "2 GB free for tool and dependencies; additional space for evidence files"],
        ["Display", "1280 x 720 minimum; 1920 x 1080 recommended for frame grid view"],
        ["Network", "Not required (tool is fully offline)"]
      ], "Component", "Specification"),
      p(""),
      h2("3.2 Software Requirements"),
      twoColTable([
        ["Operating System", "Windows 10/11, Ubuntu 20.04/22.04, macOS 11+, or WSL2"],
        ["Python", "Version 3.8 or higher (3.10+ recommended)"],
        ["pip", "Python package manager (bundled with Python 3.4+)"],
        ["Web Browser", "Google Chrome 90+, Mozilla Firefox 88+, or Microsoft Edge 90+"],
        ["Optional: ffmpeg", "For format conversion (not required for core operation)"]
      ], "Software", "Requirement"),
      p(""),
      h2("3.3 Python Library Dependencies"),
      twoColTable([
        ["flask >= 2.3.0", "Web framework for the backend API and HTML serving"],
        ["opencv-python-headless >= 4.8.0", "Video decoding, frame extraction, and image processing"],
        ["Pillow >= 10.0.0", "Image handling and JPEG export"],
        ["mutagen >= 1.47.0", "Embedded metadata extraction from video containers"],
        ["numpy >= 1.24.0", "Numerical array operations for LSB analysis"]
      ], "Library", "Purpose"),

      pageBreak(),

      // ── SECTION 4: INSTALLATION ─────────────────────────────────────────────
      h1("4. Installation Steps"),
      p("Follow these steps in order. All commands are run in a terminal (Command Prompt / PowerShell on Windows, or Terminal on Linux/macOS)."),
      p(""),
      h2("Step 1 — Extract the Project"),
      p("Extract the project ZIP file to a folder of your choice:"),
      code("unzip VideoForensicsTool.zip"),
      code("cd VideoForensicsTool"),
      p(""),
      h2("Step 2 — Create a Virtual Environment"),
      p("A virtual environment isolates the project's dependencies from your system Python installation. This is strongly recommended."),
      p("Windows:"),
      code("python -m venv venv"),
      code("venv\\Scripts\\activate"),
      p("Linux / macOS:"),
      code("python3 -m venv venv"),
      code("source venv/bin/activate"),
      p("You will see (venv) at the start of your terminal prompt when the environment is active."),
      p(""),
      h2("Step 3 — Install Dependencies"),
      code("pip install -r requirements.txt"),
      p("This installs all required Python libraries. The process takes approximately 1-3 minutes depending on your internet speed."),
      p(""),
      h2("Step 4 — Verify Installation"),
      code("python -c \"import cv2, flask, mutagen, numpy; print('All dependencies OK')\""),
      p("Expected output: All dependencies OK"),
      p(""),
      h2("Step 5 — Generate Test Videos (Optional but Recommended)"),
      code("python generate_test_videos.py"),
      p("This creates three test videos in the test_videos/ folder that you can use immediately to test the tool. See Section 6 for test scenarios."),
      p(""),
      h2("Step 6 — Fix for Ubuntu / Linux (if OpenCV fails)"),
      p("If you encounter a libGL error on Ubuntu/Debian:"),
      code("sudo apt-get install libgl1-mesa-glx libglib2.0-0"),
      p("Then retry the dependency install."),

      pageBreak(),

      // ── SECTION 5: STEP-BY-STEP USAGE ──────────────────────────────────────
      h1("5. Step-by-Step Usage Instructions"),
      h2("5.1 Starting the Tool"),
      numbered("Open a terminal in the VideoForensicsTool/ directory"),
      numbered("Activate the virtual environment (if using one)"),
      numbered("Run the application:"),
      code("python app.py"),
      numbered("Open your web browser and go to: http://localhost:5000"),
      p("The CyberTriage interface will load. The status bar at the bottom of the screen shows the current state of analysis."),
      p(""),
      h2("5.2 Loading Video Evidence"),
      numbered("Click the drop zone in the left sidebar labeled Evidence Input"),
      numbered("Browse to your video file, or drag and drop the file onto the drop zone"),
      numbered("Wait for the upload to complete (a loading indicator appears)"),
      p("Upon successful upload, the sidebar displays a file information card showing:"),
      bullet("File name, duration, resolution, FPS, file size, frame count, and codec"),
      bullet("The Video Player tab automatically loads the video for playback"),
      bullet("The Metadata tab is populated with all extracted metadata"),
      p(""),
      h2("5.3 Playing the Video"),
      p("The Video Player tab provides full playback controls:"),
      bullet("Play / Pause: Click the play button or use the spacebar"),
      bullet("Seek: Drag the progress bar to any point in the video"),
      bullet("Skip: Use the back/forward buttons to jump 10 seconds"),
      bullet("Volume: Drag the volume slider"),
      bullet("Speed: Select playback speed (0.5×, 1×, 1.5×, 2×)"),
      bullet("Capture Frame: Click the camera icon to add the current timestamp to the extraction list"),
      p(""),
      h2("5.4 Extracting Frames"),
      h3("Method A: Specific Timestamps"),
      numbered("Click the Timestamps tab in the Frame Extraction section of the sidebar"),
      numbered("In the input field, type a timestamp (e.g., 10 for 10 seconds, 1:30 for 1 minute 30 seconds, 2:45:00 for 2 hours 45 minutes)"),
      numbered("Press Enter or click the + button to add the timestamp. Multiple timestamps can be added comma-separated (e.g., 5, 10, 1:30)"),
      numbered("Added timestamps appear as chips below the input field. Click the X on a chip to remove it"),
      numbered("Click Extract Frames"),
      h3("Method B: Regular Interval"),
      numbered("Click the Interval tab in the Frame Extraction section"),
      numbered("Enter the interval in seconds (e.g., 10 to capture a frame every 10 seconds)"),
      numbered("Click Extract Frames"),
      p("Extracted frames appear in the Frames tab as a grid. Click any frame thumbnail to zoom in. Click the download icon on each frame to save it. The frame count is shown in the tab header."),
      p(""),
      h2("5.5 Steganography Analysis"),
      numbered("Load a video file (see 5.2)"),
      numbered("Click Analyze for Hidden Data in the Steganography section of the sidebar"),
      numbered("Wait for the analysis to complete (scanning large files may take 10-30 seconds)"),
      numbered("The Steganography tab opens automatically showing a summary and list of findings"),
      p("Each finding includes:"),
      bullet("Type: The detection method that triggered (e.g., Appended Data, Embedded JPEG Signature)"),
      bullet("Severity: HIGH, MEDIUM, or INFO"),
      bullet("Description: Plain-language explanation of the finding"),
      bullet("Technical details: Byte offset, size, magic bytes, or tag value"),
      bullet("Attempt Recovery button (for recoverable findings)"),
      p(""),
      h2("5.6 Recovering Hidden Data"),
      numbered("In the Steganography tab, find a finding with the Attempt Recovery button"),
      numbered("Click Attempt Recovery"),
      numbered("The tool extracts the bytes starting from the detected offset and saves them as a file"),
      numbered("A download link appears: click it to download and inspect the recovered file"),
      p("Recovered files are saved in static/recovered/<session_id>/ on the server."),
      p(""),
      h2("5.7 Viewing Metadata"),
      p("Click the Metadata tab to see a structured view of all video properties:"),
      bullet("Video Properties: resolution, duration, FPS, frame count, codec"),
      bullet("File Properties: MIME type, file size, creation time, modification time"),
      bullet("Chain of Custody: MD5 hash, SHA-256 hash"),
      bullet("Embedded Tags: All metadata tags from the video container (if any)"),
      p(""),
      h2("5.8 Generating a Report"),
      numbered("Fill in the Investigator Name and Case Number fields in the left sidebar"),
      numbered("Click Generate Report"),
      numbered("The Report tab opens showing the full structured JSON report"),
      numbered("Click Download JSON Report to save the report file"),
      p("The report includes: report ID, timestamp, case information, evidence hashes, all extracted frames, all steganography findings, and a summary."),

      pageBreak(),

      // ── SECTION 6: EXAMPLE CASES ────────────────────────────────────────────
      h1("6. Example Cases with Test Scenarios"),
      p("Three test videos are included (generated by generate_test_videos.py). The following scenarios demonstrate each major feature."),
      p(""),
      h2("6.1 Case Alpha — Standard Video Frame Extraction"),
      p("Scenario: An investigator receives test_normal.mp4 (30 seconds, color bars) and needs to capture frames at specific moments."),
      twoColTable([
        ["Test File", "test_videos/test_normal.mp4"],
        ["Duration", "30 seconds"],
        ["Features Tested", "Frame extraction (timestamps + interval), video playback, metadata, report"],
        ["Timestamps to Use", "0, 5, 10, 15, 20, 25"],
        ["Interval to Use", "5 seconds"]
      ], "Parameter", "Value"),
      p(""),
      p("Steps:"),
      numbered("Upload test_normal.mp4"),
      numbered("Observe the file info card (640x360, 25fps, approx. 1.0 MB)"),
      numbered("Play the video to verify the player works"),
      numbered("Switch to Timestamps mode, enter: 0, 5, 10, 15, 20, 25 and click Extract Frames"),
      numbered("6 frames should appear in the Frames tab"),
      numbered("Switch to Interval mode, set interval = 5, extract — should yield 7 frames (0,5,10,15,20,25,30)"),
      numbered("Click a frame to zoom in, verify the timestamp matches the frame content"),
      numbered("Go to Metadata tab — verify MD5 and SHA-256 are shown"),
      numbered("Enter investigator name and case number, generate report, download it"),
      p(""),
      h2("6.2 Case Beta — Steganography Detection and Recovery"),
      p("Scenario: A suspect video test_steg.mp4 is received. Intelligence suggests hidden data may be embedded. CyberTriage is used to detect and recover it."),
      twoColTable([
        ["Test File", "test_videos/test_steg.mp4"],
        ["Duration", "20 seconds"],
        ["Hidden Payload", "JPEG image (red square with text) appended after MP4 container"],
        ["Features Tested", "Steganography detection, hidden data recovery"],
        ["Expected Finding", "Appended Data after MP4 container (HIGH severity)"]
      ], "Parameter", "Value"),
      p(""),
      p("Steps:"),
      numbered("Upload test_steg.mp4"),
      numbered("Click Analyze for Hidden Data in the sidebar"),
      numbered("In the Steganography tab: observe HIGH severity finding — Appended Data after MP4 container"),
      numbered("Note the offset and size of the appended data"),
      numbered("Click Attempt Recovery on that finding"),
      numbered("Download the recovered .jpg file"),
      numbered("Open the recovered file — it should be a red rectangle with the text SECRET DATA"),
      numbered("This demonstrates that the video appeared normal but contained hidden binary data after the container end"),
      p(""),
      h2("6.3 Case Gamma — Metadata and Embedded File Signature Scan"),
      p("Scenario: A video from an unknown source is analyzed for metadata and embedded file signatures."),
      twoColTable([
        ["Test File", "test_videos/test_metadata.mp4"],
        ["Duration", "15 seconds"],
        ["Features Tested", "Metadata extraction, embedded file scanning"]
      ], "Parameter", "Value"),
      p(""),
      p("Steps:"),
      numbered("Upload test_metadata.mp4"),
      numbered("Go to Metadata tab — inspect all fields"),
      numbered("Run Analyze for Hidden Data"),
      numbered("Review any findings (may vary based on file content)"),
      p(""),
      h2("6.4 Format Compatibility Test"),
      p("If ffmpeg is installed, convert the test video to other formats and upload each:"),
      code("ffmpeg -i test_videos/test_normal.mp4 test_videos/test_normal.avi"),
      code("ffmpeg -i test_videos/test_normal.mp4 test_videos/test_normal.mkv"),
      code("ffmpeg -i test_videos/test_normal.mp4 test_videos/test_normal.mov"),
      p("Upload each converted file to verify CyberTriage accepts all formats."),
      p(""),
      p("For real-world testing, NIST provides free forensic video images at: https://cfreds.nist.gov/"),

      pageBreak(),

      // ── SECTION 7: INTERPRETATION ────────────────────────────────────────────
      h1("7. Interpretation of Results"),
      h2("7.1 Frame Extraction Results"),
      p("Each extracted frame represents a single video frame at the specified time. Forensic relevance:"),
      bullet("Frames extracted at key timestamps provide timestamped visual evidence of video content at specific moments."),
      bullet("Frame filename encodes the exact timestamp (e.g., frame_00_00_10_10000.jpg = 10 seconds into the video)."),
      bullet("Frame dimensions match the video's native resolution, ensuring no quality degradation."),
      bullet("Multiple frames enable side-by-side comparison of content across the timeline."),
      p(""),
      h2("7.2 Steganography Finding Interpretation"),
      twoColTable([
        ["HIGH / Appended Data", "Data exists beyond the valid container boundary. This is a strong indicator of deliberate concealment. Attempt recovery immediately."],
        ["HIGH / Embedded File Signature", "Magic bytes of a known file type found at an unexpected offset. Hidden document, image, or archive may be present."],
        ["MEDIUM / Suspicious Metadata", "A metadata tag contains a suspicious keyword or has an anomalously large value. May contain encoded payloads."],
        ["MEDIUM / LSB Anomaly", "Pixel LSB distribution deviates from the expected 50% pattern. Possible LSB steganography across frames."],
        ["INFO", "Analysis error or informational note. Does not indicate steganography. Review the description for context."]
      ], "Finding Type", "Forensic Interpretation"),
      p(""),
      h2("7.3 Metadata Interpretation"),
      twoColTable([
        ["MD5 Hash", "Verify this matches the hash of the original evidence file. A mismatch indicates tampering or corruption."],
        ["SHA-256 Hash", "Stronger cryptographic hash. Record this in the case notes as the definitive integrity marker."],
        ["Creation/Modification Times", "These timestamps may have forensic significance. Note that file system timestamps can be forged."],
        ["Embedded Tags", "May reveal camera model, GPS coordinates, software version, or other metadata. Look for unexpected or large tag values."]
      ], "Field", "Forensic Relevance"),

      pageBreak(),

      // ── SECTION 8: WORK DIVISION ─────────────────────────────────────────────
      h1("8. Work Division of All Members"),
      p("The following table documents the technical contributions of each group member. All contributions are technical (module development):"),
      twoColTable([
        ["Member 1", "Flask backend (app.py): upload endpoint, frame extraction engine (extract_frames, extract_frames_interval), file hash computation, video metadata extraction using OpenCV and Mutagen"],
        ["Member 2", "Steganography detection engine: container boundary analysis (detect_appended_data), embedded file signature scanner (detect_embedded_files), hidden data recovery (recover_hidden_data)"],
        ["Member 3", "Metadata steganography detection (detect_metadata_steganography), LSB statistical analysis (detect_lsb_hints), report generation endpoint, JSON report schema design"],
        ["Member 4", "Web interface (templates/index.html): complete frontend design, JavaScript state management, video player controls, frame grid rendering, steganography results UI, test video generator (generate_test_videos.py)"]
      ], "Member", "Technical Contribution"),

      pageBreak(),

      // ── SECTION 9: CLO ALIGNMENT ─────────────────────────────────────────────
      h1("9. CLO Alignment and Rubric Coverage"),
      h2("9.1 User Guide Rubric"),
      rubricTable([
        ["Content completeness", "10", "CLO 3", "All 8 required sections covered with detailed prose"],
        ["Installation & setup clarity", "10", "CLO 2", "Step-by-step commands for all platforms in Section 4"],
        ["Usage instructions", "10", "CLO 2", "Sub-step instructions for every feature in Section 5"],
        ["Screenshots & examples", "10", "CLO 3", "Three worked example cases with explicit steps in Section 6"],
        ["Legal & ethical considerations", "10", "CLO 1", "Full Section 2 covering laws, chain of custody, privacy, ethics"]
      ]),
      p(""),
      h2("9.2 Tool Features vs CLO Mapping"),
      twoColTable([
        ["Multi-format video ingestion", "CLO 2 — Apply digital forensics tools across multiple platforms"],
        ["Frame extraction (timestamps + interval)", "CLO 2 — Apply forensic techniques (file/media analysis)"],
        ["In-browser video playback", "CLO 2 — Tool functionality beyond minimum requirements"],
        ["Steganography detection (4 methods)", "CLO 2 — Forensic techniques; CLO 3 — Report findings"],
        ["Hidden data recovery", "CLO 2 — Beyond minimum requirements (innovation)"],
        ["MD5/SHA-256 hash computation", "CLO 1 — Evidence integrity; CLO 2 — Forensic methodology"],
        ["Structured JSON forensic report", "CLO 3 — Generate reports for security platforms"],
        ["Chain of custody fields in report", "CLO 1 — Evidence handling standards"]
      ], "Feature", "CLO Mapping")
    ]
  }]
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync('/home/claude/VideoForensicsTool/UserGuide.docx', buf);
  console.log('UserGuide.docx written successfully');
}).catch(err => {
  console.error('Error:', err);
  process.exit(1);
});
