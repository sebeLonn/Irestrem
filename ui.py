import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
import threading
import queue
import time
from pathlib import Path
from typing import Optional

from detector import FaceDistanceDetector, DetectionResult
from tracker import SessionTracker
from notifier import send_break_reminder

# ── colour palette ────────────────────────────────────────────────────────────
BG     = '#1a1a2e'
BG2    = '#16213e'
BG3    = '#0f3460'
ACCENT = '#e94560'
FG     = '#e0e0e0'
FG_DIM = '#888899'

STATUS_COLORS = {
    'too_close': '#ff4444',
    'close':     '#ff8c00',
    'good':      '#44bb44',
    'far':       '#4499ff',
    'no_face':   '#888899',
}
STATUS_LABELS = {
    'too_close': 'Too close — move back!',
    'close':     'Slightly close',
    'good':      'Good distance',
    'far':       'Good distance (far)',
    'no_face':   'No face detected',
}

CAMERA_W, CAMERA_H = 320, 240
INFO_W = 240
POLL_MS = 33        # ~30 fps UI refresh
DETECT_EVERY = 2    # run face detection every N frames; draw all frames
# ─────────────────────────────────────────────────────────────────────────────


class IrestremApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Irestrem')
        self.root.configure(bg=BG)
        self.root.resizable(True, True)
        self.root.minsize(580, 520)
        self.root.geometry('760x560')

        self.detector = FaceDistanceDetector()
        self.tracker = SessionTracker()

        self.cap: Optional[cv2.VideoCapture] = None
        self.running = False
        # Camera thread puts raw BGR numpy arrays here
        self._frame_queue: queue.Queue = queue.Queue(maxsize=3)
        self._current_result: Optional[DetectionResult] = None
        self._photo = None          # prevent GC
        self._cam_image_id = None
        self._break_window: Optional[tk.Toplevel] = None

        self._cam_target_w = CAMERA_W
        self._cam_target_h = CAMERA_H

        self._build_ui()
        self._set_window_icon()
        self._setup_status_bar()
        self._start_camera()
        self._poll()
        self.root.protocol('WM_DELETE_WINDOW', self._on_close)

    # ── Icon & status bar ────────────────────────────────────────────────────

    def _set_window_icon(self):
        icon_path = Path(__file__).parent / 'AppIcon.png'
        if icon_path.exists():
            try:
                img = Image.open(icon_path).resize((64, 64), Image.LANCZOS)
                self._icon_photo = ImageTk.PhotoImage(img)
                self.root.iconphoto(True, self._icon_photo)
            except Exception:
                pass

    def _setup_status_bar(self):
        """Add a macOS menu-bar status item showing the break countdown."""
        self._ns_status_item = None
        try:
            from AppKit import (NSStatusBar, NSVariableStatusItemLength,
                                NSMenu, NSMenuItem)
            bar = NSStatusBar.systemStatusBar()
            item = bar.statusItemWithLength_(NSVariableStatusItemLength)
            item.button().setTitle_('👁 --:--')
            item.button().setToolTip_('Irestrem — eye break timer')

            menu = NSMenu.alloc().init()
            quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                'Quit Irestrem', 'terminate:', '')
            menu.addItem_(quit_item)
            item.setMenu_(menu)

            self._ns_status_item = item
        except Exception:
            pass  # pyobjc not installed — status bar item skipped

    def _update_status_bar(self, secs: float, in_break: bool):
        if self._ns_status_item is None:
            return
        try:
            if in_break:
                remaining = self.tracker.get_break_timer() or 0
                label = f'👁 REST {int(remaining)}s'
            else:
                m, s = divmod(int(secs), 60)
                label = f'👁 {m:02d}:{s:02d}'
            self._ns_status_item.button().setTitle_(label)
        except Exception:
            pass

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)
        self._build_header()
        self._build_body()
        self._build_footer()

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=BG2, pady=8)
        hdr.grid(row=0, column=0, sticky='ew')

        tk.Label(hdr, text='Irestrem', font=('Helvetica', 17, 'bold'),
                 fg=ACCENT, bg=BG2).pack(side='left', padx=16)

        self._status_color_dot = tk.Label(hdr, text='●', font=('Helvetica', 15),
                                          fg=FG_DIM, bg=BG2)
        self._status_color_dot.pack(side='right', padx=4)

        self._status_txt = tk.Label(hdr, text='Starting…', font=('Helvetica', 10),
                                    fg=FG_DIM, bg=BG2)
        self._status_txt.pack(side='right', padx=4)

    def _build_body(self):
        body = tk.Frame(self.root, bg=BG, padx=12, pady=10)
        body.grid(row=1, column=0, sticky='nsew')

        # Info panel — fixed width, packed first so it never gets squeezed
        info_panel = tk.Frame(body, bg=BG, width=INFO_W)
        info_panel.pack(side='right', fill='y')
        info_panel.pack_propagate(False)
        self._build_info_panel(info_panel)

        # Camera area — fills remaining space
        cam_frame = tk.Frame(body, bg=BG3)
        cam_frame.pack(side='left', fill='both', expand=True, padx=(0, 12))

        self._cam_canvas = tk.Canvas(cam_frame, bg=BG3, highlightthickness=0)
        self._cam_canvas.pack(fill='both', expand=True)
        self._cam_canvas.bind('<Configure>', self._on_cam_resize)

        tk.Label(cam_frame, text='Live camera preview', font=('Helvetica', 8),
                 fg=FG_DIM, bg=BG3).pack(side='bottom', pady=2)

    def _on_cam_resize(self, event):
        if event.width > 20 and event.height > 20:
            self._cam_target_w = event.width
            self._cam_target_h = event.height

    def _build_info_panel(self, panel):
        # Distance card
        self._dist_label = self._card(
            panel, 'Distance to Screen',
            font=('Helvetica', 28, 'bold'), text='-- cm',
        )

        # Break countdown card
        break_card = tk.LabelFrame(panel, text='Next Eye Break',
                                   fg=ACCENT, bg=BG, font=('Helvetica', 9, 'bold'),
                                   pady=4, padx=8)
        break_card.pack(fill='x', pady=(0, 10))

        self._timer_label = tk.Label(break_card, text='20:00',
                                     font=('Helvetica', 22, 'bold'),
                                     fg='#44bb44', bg=BG)
        self._timer_label.pack()

        style = ttk.Style()
        style.theme_use('default')
        style.configure('EG.Horizontal.TProgressbar',
                        background='#44bb44', troughcolor=BG3, thickness=8)

        self._progress = ttk.Progressbar(break_card, mode='determinate',
                                         style='EG.Horizontal.TProgressbar')
        self._progress.pack(fill='x', pady=(2, 4))

        self._interval_label = tk.Label(break_card, text='Interval: 20 min',
                                        font=('Helvetica', 9), fg=FG_DIM, bg=BG)
        self._interval_label.pack()

        # Session stats card
        stats = tk.LabelFrame(panel, text='Session Stats',
                              fg=ACCENT, bg=BG, font=('Helvetica', 9, 'bold'),
                              pady=4, padx=8)
        stats.pack(fill='x', pady=(0, 10))

        self._session_label = tk.Label(stats, text='Duration: 0 min',
                                       font=('Helvetica', 10), fg=FG, bg=BG, anchor='w')
        self._session_label.pack(fill='x')

        self._breaks_label = tk.Label(stats, text='Breaks taken: 0',
                                      font=('Helvetica', 10), fg=FG, bg=BG, anchor='w')
        self._breaks_label.pack(fill='x')

        self._avg_label = tk.Label(stats, text='Posture avg: --',
                                   font=('Helvetica', 10), fg=FG, bg=BG, anchor='w')
        self._avg_label.pack(fill='x')

        # Buttons — anchored to bottom so they're always visible
        btn_frame = tk.Frame(panel, bg=BG)
        btn_frame.pack(side='bottom', fill='x', pady=(8, 4))

        tk.Button(btn_frame,
                  text='Take a Break Now',
                  command=self._manual_break,
                  bg='#e74c3c', fg='black',
                  font=('Helvetica', 12, 'bold'),
                  relief='flat', cursor='hand2',
                  pady=10, activebackground='#ff6b6b',
                  activeforeground='black',
                  ).pack(fill='x', pady=(0, 6))

        tk.Button(btn_frame,
                  text='Calibrate at 60 cm',
                  command=self._calibrate,
                  bg='#3498db', fg='black',
                  font=('Helvetica', 11, 'bold'),
                  relief='flat', cursor='hand2',
                  pady=9, activebackground='#5dade2',
                  activeforeground='black',
                  ).pack(fill='x')

    def _card(self, parent, title, font, text) -> tk.Label:
        lf = tk.LabelFrame(parent, text=title, fg=ACCENT, bg=BG,
                            font=('Helvetica', 9, 'bold'), pady=4, padx=8)
        lf.pack(fill='x', pady=(0, 10))
        lbl = tk.Label(lf, text=text, font=font, fg=FG, bg=BG)
        lbl.pack()
        return lbl

    def _build_footer(self):
        footer = tk.Frame(self.root, bg=BG2, pady=5)
        footer.grid(row=2, column=0, sticky='ew')
        tk.Label(footer,
                 text='20-20-20 rule: every 20 min, look 6 m away for 20 s',
                 font=('Helvetica', 8), fg=FG_DIM, bg=BG2).pack()

    # ── Camera thread ─────────────────────────────────────────────────────────

    def _start_camera(self):
        # Camera is opened inside the thread to avoid NSRunLoop conflict with Tk
        self.running = True
        threading.Thread(target=self._camera_loop, daemon=True).start()

    def _camera_loop(self):
        """Open camera in background thread, then read frames continuously."""
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.root.after(0, lambda: messagebox.showerror(
                'Camera Error',
                'Cannot open the camera.\n'
                'Please grant camera access in System Settings → Privacy & Security → Camera,\n'
                'then restart Irestrem.'))
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_W)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_H)
        cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap = cap   # expose to main thread for calibration

        frame_count = 0
        last_result = DetectionResult(None, None, 'no_face')

        while self.running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.05)
                continue

            frame = cv2.flip(frame, 1)
            frame_count += 1

            if frame_count % DETECT_EVERY == 0:
                _, last_result = self.detector.process_frame(frame)
                self._current_result = last_result
                self.tracker.update_status(last_result.status)

            annotated = self.detector.draw_result(frame, last_result)
            if not self._frame_queue.full():
                self._frame_queue.put(annotated)

        cap.release()

    # ── Main update loop (Tk thread) ──────────────────────────────────────────

    def _poll(self):
        # Drain queue — keep only the latest frame
        latest = None
        while not self._frame_queue.empty():
            latest = self._frame_queue.get_nowait()

        if latest is not None:
            # PhotoImage MUST be created on the main thread
            photo = self._bgr_to_photo(latest)
            self._photo = photo
            cw = self._cam_canvas.winfo_width()
            ch = self._cam_canvas.winfo_height()
            cx, cy = max(cw // 2, 1), max(ch // 2, 1)
            if self._cam_image_id is None:
                self._cam_image_id = self._cam_canvas.create_image(
                    cx, cy, anchor='center', image=self._photo)
            else:
                self._cam_canvas.coords(self._cam_image_id, cx, cy)
                self._cam_canvas.itemconfig(self._cam_image_id, image=self._photo)

        self._refresh_ui()
        self.root.after(POLL_MS, self._poll)

    def _bgr_to_photo(self, frame: np.ndarray) -> ImageTk.PhotoImage:
        tw = max(self._cam_target_w, CAMERA_W)
        th = max(self._cam_target_h, CAMERA_H)
        src_h, src_w = frame.shape[:2]
        ratio = min(tw / src_w, th / src_h)
        nw, nh = int(src_w * ratio), int(src_h * ratio)
        resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LINEAR)
        canvas = np.full((th, tw, 3), (15, 52, 96), dtype=np.uint8)
        y0, x0 = (th - nh) // 2, (tw - nw) // 2
        canvas[y0:y0 + nh, x0:x0 + nw] = resized
        rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        return ImageTk.PhotoImage(Image.fromarray(rgb))

    # ── UI state refresh ──────────────────────────────────────────────────────

    def _refresh_ui(self):
        result = self._current_result
        status = result.status if result else 'no_face'
        color = STATUS_COLORS.get(status, FG_DIM)

        self._status_color_dot.config(fg=color)
        self._status_txt.config(text=STATUS_LABELS.get(status, ''), fg=color)

        if result and result.distance_cm is not None:
            self._dist_label.config(text=f'{result.distance_cm:.0f} cm', fg=color)
        else:
            self._dist_label.config(text='-- cm', fg=FG_DIM)

        secs_until = self.tracker.get_time_until_break()

        if self.tracker.in_break:
            remaining = self.tracker.get_break_timer()
            if remaining is not None:
                self._timer_label.config(text=f'REST  {int(remaining)}s', fg=ACCENT)
                if remaining <= 0:
                    self.tracker.complete_break()
                    self._close_break_window()
        else:
            m, s = divmod(int(secs_until), 60)
            self._timer_label.config(
                text=f'{m:02d}:{s:02d}',
                fg='#44bb44' if secs_until > 60 else '#ff8800',
            )
            self._progress['value'] = self.tracker.get_break_progress() * 100
            self._interval_label.config(
                text=f'Interval: {self.tracker.get_break_interval_minutes()} min')
            if self.tracker.check_break_needed():
                self._trigger_break()

        self._update_status_bar(secs_until, self.tracker.in_break)

        total_s = self.tracker.get_session_duration()
        h, rem = divmod(int(total_s), 3600)
        self._session_label.config(text=f'Duration: {h}h {rem // 60}m' if h else
                                        f'Duration: {rem // 60}m')
        self._breaks_label.config(text=f'Breaks taken: {self.tracker.breaks_taken}')
        dom = self.tracker.get_dominant_status()
        self._avg_label.config(
            text=f'Posture avg: {STATUS_LABELS.get(dom, dom).split("—")[0].strip()}')

    # ── Break handling ────────────────────────────────────────────────────────

    def _trigger_break(self):
        if self.tracker.in_break:
            return
        self.tracker.start_break()
        send_break_reminder(self.tracker.get_dominant_status(),
                            self.tracker.get_session_duration() / 60)
        self._open_break_window()

    def _manual_break(self):
        if not self.tracker.in_break:
            self._trigger_break()

    def _open_break_window(self):
        if self._break_window and self._break_window.winfo_exists():
            return

        win = tk.Toplevel(self.root)
        win.title('Irestrem — Eye Break')
        win.configure(bg=BG)
        win.resizable(True, True)
        win.minsize(360, 280)
        win.attributes('-topmost', True)

        w, h = 420, 310
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f'{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}')

        tk.Label(win, text='👁', font=('Helvetica', 44), fg=ACCENT, bg=BG).pack(pady=(20, 2))
        tk.Label(win, text='Eye Break Time!',
                 font=('Helvetica', 18, 'bold'), fg=FG, bg=BG).pack()
        tk.Label(win,
                 text='Look at something 6 meters (20 feet) away\n'
                      'for 20 seconds to reduce eye strain.',
                 font=('Helvetica', 11), fg=FG_DIM, bg=BG, justify='center').pack(pady=8)

        countdown = tk.Label(win, text='20', font=('Helvetica', 38, 'bold'),
                              fg='#44bb44', bg=BG)
        countdown.pack()

        btn_row = tk.Frame(win, bg=BG)
        btn_row.pack(pady=14)

        def done():
            self.tracker.complete_break()
            self._close_break_window()

        def skip():
            self.tracker.skip_break()
            self._close_break_window()

        tk.Button(btn_row, text='Done — I took a break',
                  command=done, bg='#27ae60', fg='white',
                  font=('Helvetica', 11, 'bold'), relief='flat',
                  padx=14, pady=8, cursor='hand2').pack(side='left', padx=6)

        tk.Button(btn_row, text='Skip',
                  command=skip, bg='#555566', fg=FG,
                  font=('Helvetica', 11), relief='flat',
                  padx=14, pady=8, cursor='hand2').pack(side='left', padx=6)

        def tick():
            if not win.winfo_exists():
                return
            remaining = self.tracker.get_break_timer()
            if remaining is None:
                return
            countdown.config(text=str(int(remaining)))
            win.after(200, tick) if remaining > 0 else done()

        win.after(200, tick)
        win.protocol('WM_DELETE_WINDOW', skip)
        self._break_window = win

    def _close_break_window(self):
        if self._break_window and self._break_window.winfo_exists():
            self._break_window.destroy()
        self._break_window = None

    # ── Calibration ───────────────────────────────────────────────────────────

    def _calibrate(self):
        if not self.cap or not self.cap.isOpened():
            messagebox.showerror('Error', 'Camera not available.')
            return
        messagebox.showinfo('Calibrate',
                            'Sit exactly 60 cm from your webcam,\n'
                            'face the camera, then click OK.')
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            if self.detector.calibrate(60.0, frame):
                messagebox.showinfo('Calibration', 'Calibration successful!')
            else:
                messagebox.showwarning('Calibration',
                                       'Face not detected. Please try again.')

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _on_close(self):
        self.running = False  # signals camera thread to exit and release cap
        self.root.destroy()

    def run(self):
        self.root.mainloop()
