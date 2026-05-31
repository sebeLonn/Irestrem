"""
Attention Monitor — Teacher App
=================================
Double-click to launch. Connects to the hosted Railway server and opens
the live dashboard. No local server is started.
"""

import tkinter as tk
from tkinter import messagebox

from teacher_dashboard import TeacherDashboard

SERVER_URL    = 'https://irestrem-production.up.railway.app'
STUDENT_URL   = 'irestrem-production.up.railway.app'


if __name__ == '__main__':
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(
        'Attention Monitor — Teacher',
        f'Connected to server!\n\n'
        f'Share this address with your students:\n\n'
        f'    {STUDENT_URL}\n\n'
        f'Students enter this when they launch Attention Monitor.',
    )
    root.destroy()

    TeacherDashboard(SERVER_URL).run()
