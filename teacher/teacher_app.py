"""
Attention Monitor — Teacher App
=================================
Double-click to launch. Starts the server and dashboard together.
No terminal needed.
"""

import socket
import threading
import tkinter as tk
from tkinter import messagebox
from http.server import HTTPServer

import attention_server
from attention_server import _Handler
from teacher_dashboard import TeacherDashboard

PORT = 8765


def _local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


def _start_server() -> None:
    server = HTTPServer(('0.0.0.0', PORT), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()


if __name__ == '__main__':
    _start_server()

    local_ip = _local_ip()
    student_url = f'{local_ip}:{PORT}'

    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(
        'Attention Monitor — Teacher',
        f'Server started!\n\n'
        f'Share this address with your students:\n\n'
        f'    {student_url}\n\n'
        f'Students enter this when they launch Attention Monitor.',
    )
    root.destroy()

    TeacherDashboard(f'http://localhost:{PORT}').run()
