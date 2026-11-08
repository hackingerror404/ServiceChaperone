"""A tiny local web server for trying out website checks by hand.

This is a development tool built with Claude. It is not part of the installed package.

Run it in one terminal:   python dev/fake_server.py
Then run, in another:     python dev/try_website_check.py

Routes:
    /ok        replies 200
    /error     replies 500
    /slow      waits 60 seconds before replying (simulates a hung server)
    /redirect  replies 302, pointing at /ok
"""

import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = 8765

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/ok":
            self._reply(200, "ok")
        elif self.path == "/error":
            self._reply(500, "something broke")
        elif self.path == "/slow":
            time.sleep(60)
            self._reply(200, "finally")
        elif self.path == "/redirect":
            self._reply(302, "moved", headers={"Location": "/ok"})
        else:
            self._reply(404, "not found")

    def _reply(self, status, body, headers=None):
        data = body.encode()
        try:
            self.send_response(status)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(data)))
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass  # the client gave up waiting (that is what /slow is for)

    def log_message(self, format, *args):
        print(f"{self.command} {self.path} -> served")

class Server(ThreadingHTTPServer):
    daemon_threads = True  # so a sleeping /slow request can't block Ctrl-C

if __name__ == "__main__":
    server = Server((HOST, PORT), Handler)
    print(f"Fake server on http://{HOST}:{PORT}  (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")