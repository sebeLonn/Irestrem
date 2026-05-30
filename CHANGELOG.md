# Changelog

All notable changes to this project are documented here.

---

## [1.2.0] — 2026-05-30

### Student client
- Camera capture moved from a background thread to the Tkinter main thread via `root.after(33, _camera_step)`, eliminating a macOS AVFoundation / NSRunLoop conflict that could cause intermittent crashes on Apple Silicon.
- HTTPS is now the default scheme when the student enters a bare `host:port` address (previously defaulted to HTTP).
- SSL certificate verification uses an unverified context for local-network servers, so self-signed setups work out of the box without manual cert installation.
- Removed the intermediate `queue.Queue` between the camera and sender threads — UI is updated directly in `_camera_step`, reducing latency.
- Camera is released cleanly on window close.
- `certifi` added to the py2app bundle and `student/requirements.txt`.

### Teacher dashboard & server
- Added **Clear All Students** button in the dashboard header.
- New server endpoint `DELETE /clear` (also accepts `GET /clear`) — removes all current student entries from memory so the teacher can reset the list mid-session without restarting.

### Build
- `strip: False` set in all three `setup.py` files to preserve debug symbols and avoid strip-related build failures on newer Xcode toolchains.
- All bundle versions bumped to `1.2.0`.

---

## [1.1.0] — 2026-05-01

### Added
- **Attention Monitor system** — real-time classroom attention tracking that works alongside any video conferencing app (Zoom, Google Meet, Microsoft Teams).
- Student package (`student/`) with `AttentionMonitor.app` — double-clickable macOS app bundle, no terminal needed.
- Teacher package (`teacher/`) with `TeacherDashboard.app` — starts the HTTP server automatically and shows a live grid of student attention states.
- `attention_monitor.py` — standalone gaze detection module (face + eye Haar cascades, majority-vote smoothing, rolling attention score).
- `teacher/attention_server.py` — minimal stdlib HTTP server (`POST /update`, `GET /students`, `GET /status`).
- `teacher/teacher_dashboard.py` — Tkinter dashboard with per-student cards sorted by urgency.
- `teacher/teacher_app.py` — combined launcher that starts the server thread, detects the local IP, and opens the dashboard.
- Project separated into two self-contained packages so students receive only the files they need.

---

## [1.0.0] — 2026-04-15

### Added
- **Eye Strain Prevention app** (`main.py`, `ui.py`, `detector.py`, `tracker.py`, `notifier.py`).
- Real-time face distance estimation using OpenCV Haar cascades and the pinhole camera model.
- Dynamic break scheduling: interval adapts to measured distance (8 / 12 / 20 / 25 minutes).
- Live camera preview with colour-coded bounding box.
- Full-screen 20-second eye-break pop-up with countdown.
- macOS menu bar status item (`👁 MM:SS`) via PyObjC.
- Native macOS system notifications (osascript) with Ping sound.
- Session statistics: duration, breaks taken, dominant posture.
- One-click calibration at a known 60 cm reference distance.
- `app_icon.py` — programmatic icon generator (PNG + ICNS, all macOS sizes).
- `setup.py` — py2app build configuration for `Irestrem.app`.
- MIT License.
