"""
Attention Monitor — Central Server
===================================
Receives attention status from student clients and serves it to the teacher dashboard.
Only JSON status is transmitted — no video, no audio.

Usage
-----
    python3 attention_server.py [--port 8765]

Then tell students to run:
    python3 student_client.py --server http://YOUR_IP:8765

And open the teacher dashboard:
    python3 teacher_dashboard.py --server http://localhost:8765
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading
import time
import argparse

# ── Shared state ─────────────────────────────────────────────────────────────

# student_name → {name, status, attention_score, away_duration_s, last_seen}
_students: dict = {}
_lock = threading.Lock()

STUDENT_TIMEOUT_S = 10  # seconds of silence → mark student as disconnected


# ── HTTP handler ─────────────────────────────────────────────────────────────

class _Handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        # CORS preflight (for browser-based dashboards)
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def do_POST(self):
        if self.path == '/update':
            n = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(n)
            try:
                data = json.loads(body)
                name = str(data.get('name', 'Unknown')).strip()
                if not name:
                    raise ValueError('name is required')
                with _lock:
                    _students[name] = {
                        'name':            name,
                        'status':          data.get('status', 'absent'),
                        'attention_score': float(data.get('attention_score', 0.0)),
                        'away_duration_s': float(data.get('away_duration_s', 0.0)),
                        'last_seen':       time.time(),
                    }
                self._send(200, {'ok': True})
            except Exception as exc:
                self._send(400, {'error': str(exc)})
        else:
            self._send(404, {'error': 'not found'})

    def do_GET(self):
        if self.path == '/students':
            now = time.time()
            with _lock:
                result = []
                for s in _students.values():
                    entry = dict(s)
                    silent_s = now - s['last_seen']
                    if silent_s > STUDENT_TIMEOUT_S:
                        # Client stopped sending — treat as disconnected
                        entry['status'] = 'absent'
                        entry['away_duration_s'] = silent_s
                    result.append(entry)
            self._send(200, result)

        elif self.path == '/status':
            self._send(200, {'students': len(_students), 'uptime_s': round(time.time() - _START, 1)})

        else:
            self._send(404, {'error': 'not found'})

    # ── helpers ───────────────────────────────────────────────────────────────

    def _send(self, code: int, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(data)

    def _cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def log_message(self, *_):
        pass  # silence per-request logs


# ── Entry point ───────────────────────────────────────────────────────────────

_START = time.time()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Attention Monitor server')
    parser.add_argument('--port', type=int, default=8765, help='Listening port (default 8765)')
    args = parser.parse_args()

    server = HTTPServer(('0.0.0.0', args.port), _Handler)

    import socket
    local_ip = socket.gethostbyname(socket.gethostname())

    print('=' * 55)
    print('  Attention Monitor Server')
    print('=' * 55)
    print(f'  Listening on port {args.port}')
    print()
    print('  Teacher dashboard:')
    print(f'    python3 teacher_dashboard.py --server http://localhost:{args.port}')
    print()
    print('  Students (share this with your class):')
    print(f'    python3 student_client.py --server http://{local_ip}:{args.port}')
    print('=' * 55)
    print('  Press Ctrl+C to stop.')
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServer stopped.')
