# 👁 Irestrem

**A macOS app that watches how close you sit to your screen — and reminds you to rest your eyes before the strain sets in.**

Irestrem uses your Mac's built-in camera to measure the distance between your face and the display in real time. It adapts the frequency of eye-rest reminders based on how close you are sitting, so the harder you're working the better it looks after you.

---

## Features

- **Real-time distance detection** — Face detection via OpenCV; distance estimated using the pinhole camera model
- **Dynamic break intervals** — Shorter breaks when you're too close, longer when your posture is good
- **Live camera preview** — Colour-coded bounding box (red → orange → green → blue) shows your status at a glance
- **Eye break pop-up** — Full-screen reminder with a 20-second countdown when a break is due
- **macOS menu bar countdown** — `👁 MM:SS` timer lives in your status bar so you never lose track
- **System notifications** — Native macOS notification with sound when each break is triggered
- **Session statistics** — Duration, breaks taken, and dominant posture for the current session
- **One-click calibration** — Improve accuracy for your specific webcam at a known 60 cm reference distance
- **Resizable window** — Camera preview scales to fill available space; info panel stays fixed

---

## The 20-20-20 Rule

> Every **20 minutes**, look at something **20 feet (6 m) away** for **20 seconds**.

Irestrem adapts this rule to your actual screen distance:

| Status | Distance | Break Every |
|--------|----------|-------------|
| 🔴 Too Close | < 40 cm | 8 minutes |
| 🟠 Close | 40 – 55 cm | 12 minutes |
| 🟢 Good | 55 – 80 cm | 20 minutes |
| 🔵 Far | > 80 cm | 25 minutes |

The active interval is based on your **dominant posture over the last 5 minutes**, so brief movements don't immediately change your schedule.

---

## Requirements

| Requirement | Version |
|-------------|---------|
| macOS | 12 Monterey or later |
| Python | 3.9 or later |
| Webcam | Any camera supported by macOS AVFoundation |

---

## Installation

**1. Clone the repository**

```bash
git clone https://github.com/sebeLonn/Irestrem.git
cd Irestrem
```

**2. Install Python dependencies**

```bash
pip3 install -r requirements.txt
```

**3. Generate the app icon**

```bash
python3 app_icon.py
```

**4. Build the macOS .app bundle**

```bash
python3 setup.py py2app --alias
```

The app is placed at `dist/Irestrem.app`.

---

## Usage

**Option A — Launch as a macOS app (recommended)**

Double-click `dist/Irestrem.app`.

> **First launch only:** macOS Gatekeeper may show a security warning because the app is not signed with an Apple Developer certificate. Right-click → **Open** → **Open** to bypass it. This is a one-time step.

**Option B — Run from Terminal**

```bash
python3 main.py
```

**Grant camera permission** when prompted (System Settings → Privacy & Security → Camera if you missed it).

---

## Calibration

The default focal length (600 px) works well for most built-in Mac webcams. For better accuracy:

1. Sit exactly **60 cm** from your webcam lens.
2. Click **"Calibrate at 60 cm"** in the app.
3. Irestrem captures your face and recalculates the focal length for your camera.

Calibration resets when the app is closed. Recalibrate if you change webcam or mount position.

---

## Project Structure

```
Irestrem/
├── main.py          # Entry point
├── ui.py            # Main app: Tkinter GUI, camera pipeline, menu bar
├── detector.py      # OpenCV face detection + distance estimation
├── tracker.py       # Session timing and break scheduling
├── notifier.py      # macOS / Linux / Windows notification dispatcher
├── app_icon.py      # Programmatic icon generator (PNG + ICNS)
├── setup.py         # py2app build configuration
├── requirements.txt # Python dependencies
└── DOCUMENTATION.txt # Full technical documentation
```

---

## How It Works

```
Camera thread                        Main thread (every 33 ms)
─────────────                        ─────────────────────────
cv2.VideoCapture(0)    ──frames──►  drain queue
  │                    (numpy BGR)   convert → ImageTk.PhotoImage
  ├─ detect every 2nd frame                  │
  ├─ draw bounding box                       ▼
  └─ push to queue              update Canvas + labels + menu bar
                                       │
                                       ▼
                                 SessionTracker
                                 (break countdown, posture history)
                                       │
                                 when time == 0
                                       │
                                       ▼
                                 Notification + Break pop-up
```

> **Key implementation detail:** `cv2.VideoCapture()` is opened inside the background thread — never on the main thread. On macOS, OpenCV's AVFoundation backend starts an `NSRunLoop` internally, which conflicts with Tkinter's `NSRunLoop` on the main thread and causes an immediate `SIGABRT` crash.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `opencv-python` | Camera capture and face detection |
| `numpy` | Frame manipulation and image compositing |
| `Pillow` | PIL → ImageTk conversion, icon generation |
| `pyobjc-framework-Cocoa` | macOS menu bar status item (NSStatusBar) |

---

## License

MIT License — see [LICENSE](LICENSE) for details.
