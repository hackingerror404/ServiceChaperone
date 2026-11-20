"""Exercise every proxy-check scenario locally, with no internet required."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
import socket
import sys
import threading
import time

from fake_proxy import FakeProxyServer
from service_chaperone.checks.proxy import check_proxy
from service_chaperone.checks.website import check_website
from service_chaperone.models import Monitor
from service_chaperone.scheduler import _format_result

class _HealthyPageHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        pass

    def do_GET(self) -> None:
        body = b"ok\n"
        self.send_response(200, "OK")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

class _UpstreamServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

def _unused_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]

def _start_upstream() -> tuple[_UpstreamServer, str]:
    server = _UpstreamServer(("127.0.0.1", 0), _HealthyPageHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    host, port = server.server_address[:2]
    return server, f"http://{host}:{port}/health"

def run_scenarios() -> int:
    upstream, upstream_url = _start_upstream()
    dead_proxy_port = _unused_port()
    dead_upstream_port = _unused_port()

    open_proxy = FakeProxyServer()
    auth_proxy = FakeProxyServer(expected_auth="alice:s3cr3tpass")
    slow_proxy = FakeProxyServer(delay=2.0)

    servers = [upstream, open_proxy, auth_proxy, slow_proxy]
    for proxy in (open_proxy, auth_proxy, slow_proxy):
        proxy.start_in_background()

    failures: list[str] = []

    def check(label: str, condition: bool, detail: str = "") -> None:
        if condition:
            print(f"[PASS] {label}")
        else:
            msg = f"[FAIL] {label}" + (f" -> {detail}" if detail else "")
            print(msg)
            failures.append(msg)

    try:
        # 1. Working proxy, test page up
        res = check_proxy(open_proxy.url, url=upstream_url, timeout=2.0)
        check(
            "Working proxy, test page up",
            res.ok and res.response_ms is not None and res.response_ms >= 0,
            repr(res),
        )

        # 2. Proxy process not running
        dead_proxy_url = f"http://127.0.0.1:{dead_proxy_port}"
        res = check_proxy(dead_proxy_url, url=upstream_url, timeout=2.0)
        check(
            "Proxy process not running",
            (not res.ok)
            and res.error is not None
            and "could not connect to the proxy" in res.error.lower(),
            repr(res),
        )

        # 3. Proxy up, test page down
        dead_page_url = f"http://127.0.0.1:{dead_upstream_port}/health"
        res = check_proxy(open_proxy.url, url=dead_page_url, timeout=2.0)
        check(
            "Proxy up, test page down (502)",
            (not res.ok) and res.error is not None and "502" in res.error,
            repr(res),
        )

        # 4. Proxy wants a login, none given
        res = check_proxy(auth_proxy.url, url=upstream_url, timeout=2.0)
        check(
            "Proxy wants login, none given (407)",
            (not res.ok) and res.error is not None and "407" in res.error,
            repr(res),
        )

        # 5. Right credentials, then wrong ones
        auth_host, auth_port = auth_proxy.server_address[:2]
        good_auth_url = f"http://alice:s3cr3tpass@{auth_host}:{auth_port}"
        bad_auth_url = f"http://alice:wrongpass@{auth_host}:{auth_port}"

        res_good = check_proxy(good_auth_url, url=upstream_url, timeout=2.0)
        res_bad = check_proxy(bad_auth_url, url=upstream_url, timeout=2.0)
        check(
            "Right credentials succeed, wrong credentials fail (407)",
            res_good.ok
            and (not res_bad.ok)
            and res_bad.error is not None
            and "407" in res_bad.error,
            f"good={res_good!r}, bad={res_bad!r}",
        )

        # 6. Proxy rejects an https:// request (CONNECT)
        res = check_proxy(open_proxy.url, url="https://example.com", timeout=2.0)
        check(
            "Proxy rejects https:// CONNECT request",
            (not res.ok)
            and res.error is not None
            and "proxy" in res.error.lower(),
            repr(res),
        )

        # 7. Proxy never answers (timeout)
        timeout = 0.5
        t0 = time.perf_counter()
        res = check_proxy(slow_proxy.url, url=upstream_url, timeout=timeout)
        elapsed = time.perf_counter() - t0
        check(
            "Unresponsive proxy times out within timeout + 1 s",
            (not res.ok)
            and res.error is not None
            and "timed out" in res.error.lower()
            and elapsed <= timeout + 1.0,
            f"elapsed={elapsed:.2f}s, res={res!r}",
        )

        # 8. Password never leaks into results, errors, repr(Monitor), or log lines
        secret = "s3cr3tpass"
        secret_dead_proxy = f"http://alice:{secret}@127.0.0.1:{dead_proxy_port}"
        secret_connect_proxy = f"http://alice:{secret}@{open_proxy.server_address[0]}:{open_proxy.server_address[1]}"
        secret_bad_scheme = f"ftp://alice:{secret}@127.0.0.1:3128"

        mon = Monitor(
            name="Secret proxy",
            type="proxy",
            interval=60,
            timeout=2.0,
            retries=1,
            url=upstream_url,
            proxy=secret_dead_proxy,
        )
        r_dead = check_proxy(secret_dead_proxy, url=upstream_url, timeout=2.0)
        r_connect = check_proxy(
            secret_connect_proxy, url="https://example.com", timeout=2.0
        )
        r_scheme = check_proxy(secret_bad_scheme, url=upstream_url, timeout=2.0)
        log_line = _format_result(mon, r_dead)

        haystack = "\n".join(
            [repr(mon), repr(r_dead), repr(r_connect), repr(r_scheme), log_line]
        )
        check(
            "Password never appears in result, error, Monitor repr, or log line",
            secret not in haystack,
            f"Found secret in: {haystack}",
        )

        # 9. Website checks ignore HTTP_PROXY / HTTPS_PROXY environment variables
        old_http = os.environ.get("HTTP_PROXY")
        old_https = os.environ.get("HTTPS_PROXY")
        os.environ["HTTP_PROXY"] = dead_proxy_url
        os.environ["HTTPS_PROXY"] = dead_proxy_url
        try:
            res = check_website(upstream_url, timeout=2.0)
        finally:
            if old_http is None:
                os.environ.pop("HTTP_PROXY", None)
            else:
                os.environ["HTTP_PROXY"] = old_http
            if old_https is None:
                os.environ.pop("HTTPS_PROXY", None)
            else:
                os.environ["HTTPS_PROXY"] = old_https

        check(
            "Website check ignores HTTP_PROXY pointing to dead proxy",
            res.ok,
            repr(res),
        )
    finally:
        for srv in servers:
            srv.shutdown()
            srv.server_close()

    print(f"\nFinished with {len(failures)} failure(s).")
    return 1 if failures else 0

if __name__ == "__main__":
    sys.exit(run_scenarios())