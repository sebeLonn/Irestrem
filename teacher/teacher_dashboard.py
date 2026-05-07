"""
Attention Monitor — Teacher Dashboard
======================================
Shows all connected students' attention status in a live grid.
The professor runs this on their own machine alongside any meeting app.

Usage
-----
    python3 teacher_dashboard.py [--server http://localhost:8765]
"""

import tkinter as tk
from tkinter import ttk
import urllib.request
import json
import threading
import datetime
import argparse

# ── Palette (matches Irestrem) ────────────────────────────────────────────────
BG     = '#1a1a2e'
BG2    = '#16213e'
BG3    = '#0f3460'
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

REFRESH_MS = 3_000   # dashboard polls the server every 3 seconds
GRID_COLS  = 3       # student cards per row
CARD_W     = 210     # px


# ── Dashboard ─────────────────────────────────────────────────────────────────

class TeacherDashboard:
    def __init__(self, server_url: str) -> None:
        self._server = server_url.rstrip('/')

        self.root = tk.Tk()
        self.root.title('Attention Monitor — Teacher Dashboard')
        self.root.configure(bg=BG)
        self.root.geometry('860x560')
        self.root.minsize(640, 400)

        self._build_ui()
        self._schedule_refresh()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)
        self._build_header()
        self._build_body()
        self._build_footer()

    def _build_header(self) -> None:
        hdr = tk.Frame(self.root, bg=BG2, pady=10)
        hdr.grid(row=0, column=0, sticky='ew')

        tk.Label(hdr, text='Attention Monitor',
                 font=('Helvetica', 16, 'bold'), fg=ACCENT, bg=BG2
                 ).pack(side='left', padx=16)

        tk.Label(hdr, text='Teacher Dashboard',
                 font=('Helvetica', 10), fg=FG_DIM, bg=BG2
                 ).pack(side='left')

        self._count_lbl = tk.Label(hdr, text='—',
                                    font=('Helvetica', 10), fg=FG_DIM, bg=BG2)
        self._count_lbl.pack(side='right', padx=16)

        # Summary dots
        self._summary_frame = tk.Frame(hdr, bg=BG2)
        self._summary_frame.pack(side='right', padx=8)

    def _build_body(self) -> None:
        body = tk.Frame(self.root, bg=BG)
        body.grid(row=1, column=0, sticky='nsew')
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)

        canvas = tk.Canvas(body, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(body, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.grid(row=0, column=1, sticky='ns')
        canvas.grid(row=0, column=0, sticky='nsew')

        self._grid_frame = tk.Frame(canvas, bg=BG)
        self._cw_id = canvas.create_window((0, 0), window=self._grid_frame, anchor='nw')

        self._grid_frame.bind('<Configure>',
                               lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',
                    lambda e: canvas.itemconfig(self._cw_id, width=e.width))

        # Empty-state label (shown when no students connected)
        self._empty_lbl = tk.Label(
            self._grid_frame,
            text='No students connected.\nWaiting for student clients to join…',
            font=('Helvetica', 12), fg=FG_DIM, bg=BG, justify='center',
        )
        self._empty_lbl.grid(row=0, column=0, columnspan=GRID_COLS, pady=60)

    def _build_footer(self) -> None:
        footer = tk.Frame(self.root, bg=BG2, pady=5)
        footer.grid(row=2, column=0, sticky='ew')

        self._conn_lbl = tk.Label(footer, text=f'Server: {self._server}',
                                   font=('Helvetica', 8), fg=FG_DIM, bg=BG2)
        self._conn_lbl.pack(side='left', padx=12)

        self._updated_lbl = tk.Label(footer, text='',
                                      font=('Helvetica', 8), fg=FG_DIM, bg=BG2)
        self._updated_lbl.pack(side='right', padx=12)

    # ── Refresh cycle ─────────────────────────────────────────────────────────

    def _schedule_refresh(self) -> None:
        threading.Thread(target=self._fetch, daemon=True).start()
        self.root.after(REFRESH_MS, self._schedule_refresh)

    def _fetch(self) -> None:
        try:
            with urllib.request.urlopen(f'{self._server}/students', timeout=5) as r:
                students = json.loads(r.read())
            self.root.after(0, lambda: self._render(students))
        except Exception as exc:
            self.root.after(0, lambda e=exc: self._conn_lbl.config(
                text=f'Connection error — {e}', fg=ACCENT))

    def _render(self, students: list) -> None:
        # Sort: most problematic first
        _order = {'absent': 0, 'looking_away': 1, 'present': 2}
        students.sort(key=lambda s: (_order.get(s['status'], 3), s['name'].lower()))

        # Rebuild grid
        for widget in self._grid_frame.winfo_children():
            widget.destroy()

        if not students:
            lbl = tk.Label(
                self._grid_frame,
                text='No students connected.\nWaiting for student clients to join…',
                font=('Helvetica', 12), fg=FG_DIM, bg=BG, justify='center',
            )
            lbl.grid(row=0, column=0, columnspan=GRID_COLS, pady=60)
        else:
            for col in range(GRID_COLS):
                self._grid_frame.columnconfigure(col, weight=1)
            for i, student in enumerate(students):
                row, col = divmod(i, GRID_COLS)
                self._make_card(student, row, col)

        # Update summary
        n        = len(students)
        present  = sum(1 for s in students if s['status'] == 'present')
        away_cnt = sum(1 for s in students if s['status'] == 'looking_away')
        absent   = sum(1 for s in students if s['status'] == 'absent')

        self._count_lbl.config(text=f'{n} student{"s" if n != 1 else ""} online')

        for w in self._summary_frame.winfo_children():
            w.destroy()
        for color, count, label in [
            (STATUS_COLORS['present'],      present,  'present'),
            (STATUS_COLORS['looking_away'], away_cnt, 'not looking'),
            (STATUS_COLORS['absent'],       absent,   'absent'),
        ]:
            if count > 0:
                tk.Label(self._summary_frame,
                         text=f'● {count} {label}',
                         font=('Helvetica', 9, 'bold'), fg=color, bg=BG2
                         ).pack(side='left', padx=6)

        self._conn_lbl.config(text=f'Server: {self._server}', fg=FG_DIM)
        self._updated_lbl.config(
            text=f'Updated: {datetime.datetime.now().strftime("%H:%M:%S")}')

    # ── Student card ──────────────────────────────────────────────────────────

    def _make_card(self, student: dict, row: int, col: int) -> None:
        status = student.get('status', 'absent')
        color  = STATUS_COLORS.get(status, FG_DIM)
        score  = int(student.get('attention_score', 0.0) * 100)
        away_s = student.get('away_duration_s', 0.0)

        # Coloured 2px left border via outer frame
        outer = tk.Frame(self._grid_frame, bg=color, padx=2, pady=2)
        outer.grid(row=row, column=col, padx=8, pady=8, sticky='nsew')

        inner = tk.Frame(outer, bg=BG2, padx=12, pady=10)
        inner.pack(fill='both', expand=True)

        # Name
        tk.Label(inner, text=student['name'],
                 font=('Helvetica', 13, 'bold'), fg=FG, bg=BG2, anchor='w'
                 ).pack(fill='x')

        # Status — large coloured badge
        badge = tk.Frame(inner, bg=color, padx=8, pady=4)
        badge.pack(fill='x', pady=(8, 4))
        tk.Label(badge, text=STATUS_LABELS.get(status, status),
                 font=('Helvetica', 11, 'bold'), fg='#ffffff', bg=color, anchor='w'
                 ).pack(fill='x')

        # Attention score bar
        bar_bg = tk.Frame(inner, bg=BG3, height=8)
        bar_bg.pack(fill='x', pady=(2, 2))
        bar_bg.pack_propagate(False)

        fill_pct = max(score / 100, 0.02)
        bar_fill = tk.Frame(bar_bg, bg=color, height=8)
        bar_fill.place(relx=0, rely=0, relwidth=fill_pct, relheight=1)

        tk.Label(inner, text=f'Attention: {score}%',
                 font=('Helvetica', 10, 'bold'), fg=color, bg=BG2, anchor='w'
                 ).pack(fill='x')

        # Away duration (only when relevant)
        if away_s >= 2.0:
            tk.Label(inner, text=f'Away for: {int(away_s)}s',
                     font=('Helvetica', 9, 'bold'), fg=ACCENT, bg=BG2, anchor='w'
                     ).pack(fill='x', pady=(2, 0))

    # ── Run ───────────────────────────────────────────────────────────────────

    def run(self) -> None:
        self.root.mainloop()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Attention Monitor — Teacher Dashboard')
    parser.add_argument('--server', default='http://localhost:8765',
                        help='Attention server URL (default: http://localhost:8765)')
    args = parser.parse_args()

    TeacherDashboard(args.server).run()
