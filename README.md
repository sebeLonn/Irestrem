# Irestrem

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

A lightweight classroom attention tracking system that works alongside any video conferencing app. Students run a small client that watches the webcam locally; the teacher sees a live dashboard showing each student's gaze status. No video is ever transmitted — only a tiny JSON status update every 2 seconds.

### How It Works

```
Student machine                       Teacher machine
───────────────                       ───────────────
Webcam → AttentionMonitor             attention_server.py (HTTP)
  │  (OpenCV face + eye detection)          │
  │  gaze_status, attention_score           │  GET /students
  └──── POST /update (JSON) ──────────────► └──► teacher_dashboard.py
        (no video, ~200 bytes/req)                (Tkinter grid, refreshes every 3 s)
```

### Gaze States

| Status | Meaning | Card colour |
|--------|---------|-------------|
| `present` | Face visible, eyes detected, facing screen | Green |
| `looking_away` | Face visible but head turned | Orange |
| `absent` | No face detected | Red |

### Running the System

**Step 1 — Start the server** (on the teacher's machine or a shared network host):

```bash
python3 attention_server.py
# Listening on port 8765
# Prints the IP address students should use
```

**Step 2 — Each student runs the client:**

```bash
python3 student_client.py --server http://TEACHER_IP:8765
# A name dialog appears on first launch
# Or pass the name directly:
python3 student_client.py --server http://192.168.1.10:8765 --name "Alice"
```

A small floating window (always on top) appears showing the student's own live status. The webcam is used locally; nothing is streamed.

**Step 3 — Teacher opens the dashboard:**

```bash
python3 teacher_dashboard.py --server http://localhost:8765
```

A dark-themed grid shows all connected students. Cards are sorted by urgency (absent → not looking → present) and update every 3 seconds.

**Demo / testing** (simulates 5 students with rotating statuses):

```bash
python3 _demo_sim.py
```

### Camera note

On macOS the webcam can be shared between apps simultaneously, so `student_client.py` and your meeting app can both use it at the same time.
On Windows, only one app can hold the camera at a time — use OBS Virtual Camera so your meeting app uses the virtual feed and `student_client.py` uses the real one.

### Integration possibilities

The server exposes a plain HTTP/JSON API, so the student client can be replaced by:

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
pip3 install -r requirements.txt
```

---

## Installation

```bash
git clone https://github.com/sebeLonn/Irestrem.git
cd Irestrem
pip3 install -r requirements.txt
```

To build the macOS `.app` bundle:

```bash
python3 app_icon.py
python3 setup.py py2app --alias
# App placed at dist/Irestrem.app
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
├── app_icon.py           Programmatic icon generator (PNG + ICNS)
├── setup.py              py2app build configuration
│
│  Attention Monitor
├── attention_monitor.py  Core gaze detection module (embeddable, OpenCV only)
├── attention_server.py   Lightweight HTTP server — receives and serves student status
├── student_client.py     Student-side client — webcam → gaze → POST to server
├── teacher_dashboard.py  Teacher dashboard — live student grid (Tkinter)
├── _demo_sim.py          Demo helper — simulates 5 students with rotating statuses
│
│  Shared
├── requirements.txt      Python dependencies
├── AppIcon.icns          App icon (all macOS sizes)
├── AppIcon.png           App icon source (512 × 512 px)
├── Irestrem.app/         macOS application bundle
├── dist/                 py2app build output
└── build/                py2app intermediate artefacts
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `opencv-python` | Camera capture, face and eye detection |
| `numpy` | Frame manipulation |
| `Pillow` | PIL → ImageTk conversion, icon generation |
| `pyobjc-framework-Cocoa` | macOS menu bar status item (NSStatusBar) |

---

## Privacy

**Eye Strain Prevention:** all video is processed in memory on your local machine. No frames, images, or data are written to disk or transmitted externally.

**Attention Monitor:** no video is ever transmitted. Only a small JSON payload (`name`, `status`, `attention_score`, `away_duration_s`) is sent from each student to the server every 2 seconds. The server holds this data in memory only — nothing is written to disk.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
