"""
Attention Monitor — Teacher App
=================================
Double-click to launch. Enter your server address, then the live
dashboard opens automatically.
"""

import tkinter as tk
from tkinter import font as tkfont
import sys

from teacher_dashboard import TeacherDashboard

# ── Palette ────────────────────────────────────────────────────────────────
BG     = '#1a1a2e'
BG2    = '#16213e'
ACCENT = '#e94560'
FG     = '#e0e0e0'
FG_DIM = '#888899'


def _ask_server() -> str | None:
    root = tk.Tk()
    root.title('Attention Monitor — Teacher')
    root.configure(bg=BG)
    root.resizable(False, False)

    w, h = 420, 260
    root.geometry(f'{w}x{h}')
    root.eval('tk::PlaceWindow . center')

    result = {'url': None}

    # ── Header ────────────────────────────────────────────────────────────
    hdr = tk.Frame(root, bg=ACCENT, height=4)
    hdr.pack(fill='x')

    title_f = tk.Frame(root, bg=BG, pady=18)
    title_f.pack(fill='x')
    tk.Label(title_f, text='Attention Monitor',
             font=('Helvetica', 16, 'bold'), fg=FG, bg=BG).pack()
    tk.Label(title_f, text='Teacher Dashboard',
             font=('Helvetica', 11), fg=FG_DIM, bg=BG).pack()

    # ── Server input ──────────────────────────────────────────────────────
    body = tk.Frame(root, bg=BG2, padx=28, pady=16)
    body.pack(fill='both', expand=True)

    tk.Label(body, text='Server address',
             font=('Helvetica', 10, 'bold'), fg=FG, bg=BG2,
             anchor='w').pack(fill='x')
    tk.Label(body,
             text='Enter the URL or IP:port of your attention server',
             font=('Helvetica', 9), fg=FG_DIM, bg=BG2,
             anchor='w').pack(fill='x', pady=(2, 8))

    entry_var = tk.StringVar(value='')
    entry = tk.Entry(body, textvariable=entry_var,
                     font=('Helvetica', 12),
                     bg='#0f3460', fg=FG, insertbackground=FG,
                     relief='flat', bd=6)
    entry.pack(fill='x', ipady=6)
    entry.focus_set()

    err_lbl = tk.Label(body, text='', fg=ACCENT, bg=BG2,
                       font=('Helvetica', 9))
    err_lbl.pack(pady=(6, 0))

    # ── Connect button ────────────────────────────────────────────────────
    def _connect(event=None):
        raw = entry_var.get().strip()
        if not raw:
            err_lbl.config(text='Please enter a server address.')
            return
        if not raw.startswith('http'):
            raw = 'https://' + raw
        result['url'] = raw
        root.destroy()

    btn_f = tk.Frame(root, bg=BG, pady=12)
    btn_f.pack(fill='x')
    tk.Button(btn_f, text='Connect →',
              command=_connect,
              bg=ACCENT, fg='white',
              font=('Helvetica', 11, 'bold'),
              relief='flat', cursor='hand2',
              padx=24, pady=8,
              activebackground='#c73652', activeforeground='white',
              ).pack()

    root.bind('<Return>', _connect)
    root.protocol('WM_DELETE_WINDOW', lambda: sys.exit(0))
    root.mainloop()

    return result['url']


if __name__ == '__main__':
    server_url = _ask_server()
    if not server_url:
        sys.exit(0)

    TeacherDashboard(server_url).run()
