"""
Attention Monitor — Student Client
====================================
Run this file during your online class. It uses your webcam locally
to detect whether you are looking at the screen, then sends only a
small status update (no video, no audio) to your teacher's server.

Usage
-----
    python3 student_client.py

You will be asked for:
  1. The server address your teacher shared with you  (e.g. 192.168.1.10:8765)
  2. Your name

Camera note
-----------
On macOS the webcam can be shared between apps simultaneously, so this
client and your meeting app (Zoom, Meet, Teams…) can both use it at once.
On Windows only one app can hold the camera at a time — in that case run
OBS Virtual Camera: your meeting app uses the virtual feed, this client
uses the real one.
"""

import tkinter as tk
from tkinter import simpledialog, messagebox
import threading
import time
import json
import urllib.request
import ssl

import cv2
from attention_monitor import AttentionMonitor, AttentionResult

# ── Palette ────────────────────────────────────────────────────────────────
BG2    = '#16213e'
ACCENT = '#e94560'
FG     = '#e0e0e0'
FG_DIM = '#888899'

STATUS_COLORS = {
    'present':      '#44bb44',
    'looking_away': '#ff8c00',
    'absent':       '#ff4444',
}
STATUS_LABELS = {
    'present':      'Looking at screen',
    'looking_away': 'Not looking',
    'absent':       'Not at desk',
}

SEND_INTERVAL_S = 2    # seconds between status POSTs
POLL_MS         = 500  # Tkinter refresh rate


# ── Startup dialog ─────────────────────────────────────────────────────────

def _ask_connection() -> tuple[str, str] | None:
    """
    Show two dialogs: server address, then student name.
    Returns (server_url, name) or None if the user cancels.
    """
    root = tk.Tk()
    root.withdraw()

    server_raw = simpledialog.askstring(
        'Attention Monitor — Connect',
        'Enter the server address your teacher gave you:\n'
        'Example: 192.168.1.10:8765',
        parent=root,
    )
    if not server_raw or not server_raw.strip():
        root.destroy()
        return None

    server_raw = server_raw.strip()
    if not server_raw.startswith('http'):
        server_raw = 'https://' + server_raw

    name = simpledialog.askstring(
        'Attention Monitor — Your Name',
        'Enter your name (as the teacher will see it):',
        parent=root,
    )
    root.destroy()

    if not name or not name.strip():
        return None

    return server_raw, name.strip()


# ── Student client ─────────────────────────────────────────────────────────

class StudentClient:
    def __init__(self, server_url: str, name: str) -> None:
        self._server = server_url.rstrip('/')
        self._name   = name

        self._monitor = AttentionMonitor()
        self._latest: AttentionResult | None = None
        self._running = False

        self.root = tk.Tk()
        self.root.title(f'Attention Monitor — {name}')
        self.root.configure(bg=BG2)
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)
        self.root.geometry('280x90')

        self._cap = None
        self._frame_n = 0
        self._running = True

        self._build_ui()
        self._start_sender()
        self.root.after(100, self._camera_step)
        self.root.protocol('WM_DELETE_WINDOW', self._on_close)

    # ── UI ────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        hdr = tk.Frame(self.root, bg=BG2, padx=10, pady=6)
        hdr.pack(fill='x')
        tk.Label(hdr, text='Attention Monitor',
                 font=('Helvetica', 10, 'bold'), fg=ACCENT, bg=BG2
                 ).pack(side='left')
        tk.Label(hdr, text=self._name,
                 font=('Helvetica', 9), fg=FG_DIM, bg=BG2
                 ).pack(side='right')

        status_row = tk.Frame(self.root, bg=BG2, padx=12, pady=2)
        status_row.pack(fill='x')
        self._dot = tk.Label(status_row, text='●', font=('Helvetica', 14),
                              fg=FG_DIM, bg=BG2)
        self._dot.pack(side='left')
        self._status_lbl = tk.Label(status_row, text='Starting…',
                                     font=('Helvetica', 10, 'bold'), fg=FG, bg=BG2)
        self._status_lbl.pack(side='left', padx=6)

        self._server_lbl = tk.Label(self.root, text='Connecting to server…',
                                     font=('Helvetica', 8), fg=FG_DIM, bg=BG2)
        self._server_lbl.pack(side='bottom', pady=(0, 5))

    # ── Camera (main thread via after()) ──────────────────────────────────

    def _camera_step(self) -> None:
        if not self._running:
            return

        if self._cap is None or not self._cap.isOpened():
            self._cap = cv2.VideoCapture(0)
            if not self._cap.isOpened():
                self.root.after(1000, self._camera_step)
                return
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  320)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
            self._cap.set(cv2.CAP_PROP_FPS, 30)

        ret, frame = self._cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            self._frame_n += 1
            if self._frame_n % 2 == 0:
                result = self._monitor.process_frame(frame)
                self._latest = result
                color = STATUS_COLORS.get(result.gaze_status, FG_DIM)
                self._dot.config(fg=color)
                self._status_lbl.config(
                    text=STATUS_LABELS.get(result.gaze_status, result.gaze_status),
                    fg=color)

        self.root.after(33, self._camera_step)

    # ── Sender thread ─────────────────────────────────────────────────────

    def _start_sender(self) -> None:
        threading.Thread(target=self._sender_loop, daemon=True).start()

    def _sender_loop(self) -> None:
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        while self._running:
            result = self._latest
            payload = json.dumps({
                'name':            self._name,
                'status':          result.gaze_status if result else 'absent',
                'attention_score': result.attention_score if result else 0.0,
                'away_duration_s': result.away_duration_s if result else 0.0,
            }).encode()
            try:
                req = urllib.request.Request(
                    f'{self._server}/update',
                    data    = payload,
                    headers = {'Content-Type': 'application/json'},
                    method  = 'POST',
                )
                urllib.request.urlopen(req, timeout=5, context=ssl_ctx)
                self.root.after(0, lambda: self._server_lbl.config(
                    text='Connected to teacher server', fg='#44bb44'))
            except Exception:
                self.root.after(0, lambda: self._server_lbl.config(
                    text='Cannot reach server — retrying…', fg=ACCENT))
            time.sleep(SEND_INTERVAL_S)

    def _on_close(self) -> None:
        self._running = False
        if self._cap:
            self._cap.release()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    result = _ask_connection()
    if result is None:
        print('Cancelled.')
        raise SystemExit(0)

    server_url, name = result
    StudentClient(server_url, name).run()
