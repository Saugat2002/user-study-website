"""
User Study Server
-----------------
Serves the study and saves submitted results to the 'results/' folder as JSON.
If the WEBHOOK_URL environment variable is set, results are also forwarded to
that URL (use a Google Apps Script web app to save to Google Sheets).

Usage (local):
    python server.py

Usage (production on Render):
    Set PORT and WEBHOOK_URL environment variables via the Render dashboard.
"""
import os
import json
import threading
import webbrowser
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, HTTPServer
from urllib.request import urlopen, Request
from urllib.error import URLError

PORT        = int(os.environ.get('PORT', 8081))
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')   # set in Render dashboard
IS_LOCAL    = not os.environ.get('RENDER')        # True when running locally


class StudyHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/save':
            length = int(self.headers.get('Content-Length', 0))
            body   = self.rfile.read(length)
            try:
                data     = json.loads(body)
                username = data.get('username', 'anonymous').strip() or 'anonymous'
                safe     = ''.join(c if c.isalnum() or c in '-_' else '_' for c in username)
                ts       = datetime.utcnow().strftime('%Y%m%dT%H%M%S')
                filename = f'{safe}_{ts}.json'

                # Save locally
                os.makedirs(RESULTS_DIR, exist_ok=True)
                filepath = os.path.join(RESULTS_DIR, filename)
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f'  [saved] {filename}')

                # Forward to Google Sheets webhook (if configured)
                if WEBHOOK_URL:
                    try:
                        req = Request(
                            WEBHOOK_URL,
                            data=body,
                            headers={'Content-Type': 'application/json'},
                            method='POST',
                        )
                        urlopen(req, timeout=10)
                        print(f'  [webhook] forwarded {filename}')
                    except URLError as e:
                        print(f'  [webhook] failed: {e}')

                response = json.dumps({'status': 'ok', 'file': filename}).encode()
            except Exception as e:
                print(f'  [error] {e}')
                response = json.dumps({'status': 'error', 'message': str(e)}).encode()

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', len(response))
            self.end_headers()
            self.wfile.write(response)
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, fmt, *args):
        if args and (args[1] == '200' and '.png' in args[0]):
            return
        super().log_message(fmt, *args)


def open_browser():
    webbrowser.open(f'http://localhost:{PORT}')


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = HTTPServer(('', PORT), StudyHandler)
    print(f'User Study Server running at http://localhost:{PORT}')
    print(f'Results will be saved to: {RESULTS_DIR}/')
    if WEBHOOK_URL:
        print(f'Webhook enabled: {WEBHOOK_URL[:60]}...')
    print('Press Ctrl+C to stop.\n')
    if IS_LOCAL:
        threading.Timer(1.0, open_browser).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServer stopped.')
