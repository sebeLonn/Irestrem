# Irestrem

**Version 1.2** &nbsp;|&nbsp; macOS &nbsp;|&nbsp; Python 3.9+ &nbsp;|&nbsp; MIT License

A macOS toolkit with two complementary tools for healthier, more focused screen use:

1. **Eye Strain Prevention** — monitors how close you sit to your screen and schedules 20-20-20 eye breaks automatically
2. **Attention Monitor** — lets a teacher see at a glance which students are paying attention during an online class session

---

## Part 1 — Eye Strain Prevention

Irestrem uses your Mac's built-in camera to measure the distance between your face and the display in real time. It adapts the frequency of eye-rest reminders based on how close you are sitting, so the harder you're working the better it looks after you.

### Features

- **Real-time distance detection** — face detection via OpenCV; distance estimated using the pinhole camera model
- **Dynamic break intervals** — shorter breaks when you're too close, longer when your posture is good
- **Live camera preview** — colour-coded bounding box (red → orange → green → blue) shows your status at a glance
- **Eye break pop-up** — full-screen reminder with a 20-second countdown when a break is due
- **macOS menu bar countdown** — `👁 MM:SS` timer lives in your status bar so you never lose track
- **System notifications** — native macOS notification with sound when each break is triggered
- **Session statistics** — duration, breaks taken, and dominant posture for the current session
- **One-click calibration** — improve accuracy for your specific webcam at a known 60 cm reference distance

### The 20-20-20 Rule

> Every **20 minutes**, look at something **20 feet (6 m) away** for **20 seconds**.

Irestrem adapts this rule to your actual screen distance:

| Status | Distance | Break Every |
|--------|----------|-------------|
| Too Close | < 40 cm | 8 minutes |
| Close | 40 – 55 cm | 12 minutes |
| Good | 55 – 80 cm | 20 minutes |
| Far | > 80 cm | 25 minutes |

### Usage

**Option A — Launch as a macOS app (recommended)**

Double-click `Irestrem.app`.

> **First launch only:** Right-click → **Open** → **Open** to bypass the Gatekeeper warning (app is unsigned).

**Option B — Terminal**

```bash
python3 main.py
```

---

## Part 2 — Attention Monitor

A lightweight classroom attention tracking system that works alongside any video conferencing app (Zoom, Google Meet, Microsoft Teams). Students run a small app that watches the webcam locally; the teacher sees a live dashboard showing each student's gaze status. No video is ever transmitted — only a tiny JSON status update every 2 seconds.

The system is split into two separate packages so students only receive what they need and never see the teacher's server or dashboard.

### How It Works

```
Student machine                       Teacher machine
───────────────                       ───────────────
Webcam → AttentionMonitor             TeacherDashboard.app
  │  (OpenCV face + eye detection)     ├─ attention_server (HTTP, port 8765)
  │  gaze_status, attention_score      │       │  GET /students
  └──── POST /update (JSON) ──────────►│       └──► teacher_dashboard (Tkinter grid)
        (no video, ~200 bytes/req)      │
                                        └─ Startup dialog shows student URL
```

### Gaze States

| Status | Meaning | Card colour |
|--------|---------|-------------|
| `present` | Face visible, eyes detected, facing screen | Green |
| `looking_away` | Face visible but head turned | Orange |
| `absent` | No face detected | Red |

### For Students — AttentionMonitor.app

1. Receive the `student/` folder from your teacher
2. Double-click `student/dist/AttentionMonitor.app`
   > First launch: Right-click → **Open** → **Open** (Gatekeeper bypass, one time only)
3. Enter the **server address** your teacher shared (e.g. `192.168.1.10:8765`)
4. Enter **your name**
5. A small floating window appears — leave it running during class

The app uses your webcam locally. No video is sent anywhere.

**macOS:** The webcam can be shared, so the Attention Monitor and your meeting app (Zoom, Meet, Teams) can both use it simultaneously.  
**Windows:** Only one app can hold the camera at a time — use OBS Virtual Camera so your meeting app uses the virtual feed and Attention Monitor uses the real one.

### For Teachers — TeacherDashboard.app

1. Double-click `teacher/dist/TeacherDashboard.app`
2. A startup dialog shows the **address to share with students** (e.g. `192.168.1.10:8765`)
3. Click OK — the live dashboard opens automatically

The server starts in the background automatically. No terminal needed.

The dashboard shows a card per connected student, sorted by urgency (absent → not looking → present), and refreshes every 3 seconds. Use the **Clear All Students** button in the header to reset the list mid-session without restarting.

### Server API

The server exposes a plain HTTP/JSON API on port 8765:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/update` | POST | Register or update a student's status |
| `/students` | GET | Return all current student statuses |
| `/status` | GET | Server health check (student count + uptime) |
| `/clear` | GET | Remove all students from memory |

Because CORS headers are set on all responses, a browser-based dashboard or extension can call the API directly with no proxy needed.

### Integration possibilities

The student client can be replaced by:

- A **browser extension** — uses `navigator.mediaDevices.getUserMedia()` and runs MediaPipe FaceMesh in-browser; works on Google Meet, Zoom Web, and Teams Web without any install
- A **Zoom / Teams app** — embed the teacher dashboard as a side panel via the Zoom Apps SDK or Microsoft Teams Toolkit
- An **LMS plugin** — POST to `/update` from any web client; embed the dashboard as an iframe in Moodle or Canvas

---

## Requirements

| Requirement | Version |
|-------------|---------|
| macOS | 12 Monterey or later |
| Python | 3.9 or later |
| Webcam | Any camera supported by macOS AVFoundation |

```bash
# Eye Strain Prevention app
pip3 install -r requirements.txt

# Student client
pip3 install -r student/requirements.txt

# Teacher dashboard (stdlib only — no extra packages)
```

---

## Installation

```bash
git clone https://github.com/sebeLonn/Irestrem.git
cd Irestrem
```

To rebuild the macOS app bundles:

```bash
# Eye Strain Prevention
python3 app_icon.py
python3 setup.py py2app --alias

# Student app
cd student && python3 setup.py py2app --alias

# Teacher app
cd teacher && python3 setup.py py2app --alias
```

---

## Project Structure

```
Irestrem/
│
│  Eye Strain Prevention
├── main.py               Entry point for the Irestrem app
├── ui.py                 Tkinter GUI, camera pipeline, macOS menu bar
├── detector.py           OpenCV face detection + pinhole distance estimation
├── tracker.py            Session timing and break scheduling
├── notifier.py           macOS / Linux / Windows notification dispatcher
├── attention_monitor.py  Core gaze detection module (shared)
├── app_icon.py           Programmatic icon generator (PNG + ICNS)
├── setup.py              py2app build configuration
├── requirements.txt      Python dependencies
│
│  Attention Monitor — Student Package
├── student/
│   ├── student_client.py      Student app — webcam → gaze → POST to server
│   ├── attention_monitor.py   Core gaze detection module (copy)
│   ├── setup.py               py2app build configuration
│   ├── requirements.txt       opencv-python, numpy, certifi
│   └── dist/
│       └── AttentionMonitor.app   Double-clickable student app
│
│  Attention Monitor — Teacher Package
├── teacher/
│   ├── teacher_app.py         Combined launcher — starts server + dashboard
│   ├── teacher_dashboard.py   Live student grid (Tkinter)
│   ├── attention_server.py    Lightweight HTTP server
│   ├── setup.py               py2app build configuration
│   ├── requirements.txt       stdlib only
│   └── dist/
│       └── TeacherDashboard.app   Double-clickable teacher app
│
│  Shared
├── CHANGELOG.md          Version history
├── AppIcon.icns          App icon (all macOS sizes)
├── AppIcon.png           App icon source (512 × 512 px)
└── Irestrem.app/         macOS application bundle (Eye Strain Prevention)
```

---

## Dependencies

| Package | Purpose | Used by |
|---------|---------|---------|
| `opencv-python` | Camera capture, face and eye detection | Irestrem, student client |
| `numpy` | Frame manipulation | Irestrem, student client |
| `Pillow` | PIL → ImageTk conversion, icon generation | Irestrem |
| `pyobjc-framework-Cocoa` | macOS menu bar status item (NSStatusBar) | Irestrem |
| `certifi` | SSL certificate bundle for HTTPS connections | Student client |

The teacher-side server and dashboard use only Python standard library — no additional packages needed.

---

## Privacy

**Eye Strain Prevention:** all video is processed in memory on your local machine. No frames, images, or data are written to disk or transmitted externally.

**Attention Monitor:** no video is ever transmitted. Only a small JSON payload (`name`, `status`, `attention_score`, `away_duration_s`) is sent from each student to the server every 2 seconds. The server holds this data in memory only — nothing is written to disk. All data is lost when the server stops.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
