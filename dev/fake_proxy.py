"""Tiny local HTTP proxy for development and testing.

Run by hand:
    python dev/fake_proxy.py --port 3128
    python dev/fake_proxy.py --port 3128 --auth alice:secret
    python dev/fake_proxy.py --port 3128 --delay 3
"""

import argparse
import base64
import http.client
import sys
import threading
import time

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

class FakeProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args) -> None:
        if not self.server.quiet:
            super().log_message(format, *args)

    def _check_auth(self) -> bool:
        expected = self.server.expected_auth
        if not expected:
            return True
        token = base64.b64encode(expected.encode("utf-8")).decode("ascii")
        if self.headers.get("Proxy-Authorization") == f"Basic {token}":
            return True
        body = b"Proxy authentication required\n"
        self.send_response(407, "Proxy Authentication Required")
        self.send_header("Proxy-Authenticate", 'Basic realm="fake-proxy"')
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        return False

    def _maybe_delay(self) -> None:
        if self.server.delay > 0:
            time.sleep(self.server.delay)

    def do_GET(self) -> None:
        self._maybe_delay()
        if not self._check_auth():
            return

        parsed = urlparse(self.path)
        if parsed.scheme != "http" or not parsed.hostname:
            body = b"Only plain http:// proxy requests are forwarded\n"
            self.send_response(400, "Bad Request")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        target_path = parsed.path or "/"
        if parsed.query:
            target_path = f"{target_path}?{parsed.query}"

        conn = http.client.HTTPConnection(
            parsed.hostname, parsed.port or 80, timeout=5
        )
        try:
            conn.request("GET", target_path)
            resp = conn.getresponse()
            body = resp.read()
        except OSError as exc:
            body = f"Upstream error: {exc}\n".encode("utf-8")
            self.send_response(502, "Bad Gateway")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
            return
        finally:
            conn.close()

        self.send_response(resp.status, resp.reason)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def do_CONNECT(self) -> None:
        self._maybe_delay()
        if not self._check_auth():
            return
        body = b"CONNECT tunneling rejected by fake proxy\n"
        self.send_response(403, "Forbidden")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

class FakeProxyServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True  # allows clean exit even if a delayed request is sleeping

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 0,
        *,
        expected_auth: str | None = None,
        delay: float = 0.0,
        quiet: bool = True,
    ) -> None:
        self.expected_auth = expected_auth
        self.delay = delay
        self.quiet = quiet
        super().__init__((host, port), FakeProxyHandler)

    @property
    def url(self) -> str:
        host, port = self.server_address[:2]
        return f"http://{host}:{port}"

    def start_in_background(self) -> threading.Thread:
        thread = threading.Thread(target=self.serve_forever, daemon=True)
        thread.start()
        return thread

    def handle_error(self, request, client_address) -> None:
        _, exc, _ = sys.exc_info()
        if isinstance(exc, (BrokenPipeError, ConnectionResetError)):
            return
        super().handle_error(request, client_address)

def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local stand-in HTTP proxy.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3128)
    parser.add_argument(
        "--auth",
        default=None,
        help="Require Basic auth in 'user:pass' format.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Seconds to sleep before answering each request.",
    )
    args = parser.parse_args()

    server = FakeProxyServer(
        args.host,
        args.port,
        expected_auth=args.auth,
        delay=args.delay,
        quiet=False,
    )
    print(f"Fake proxy listening on {server.url} (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping fake proxy.")
    finally:
        server.server_close()

if __name__ == "__main__":
    main()