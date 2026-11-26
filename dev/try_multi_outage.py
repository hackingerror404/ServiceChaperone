"""Take a local website, proxy, and TCP port down and up in turn.

Runs as a separate instance with its own temporary config so deliberate outages
never interfere with a running 72-hour soak test.

    python dev/try_multi_outage.py
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time

from apscheduler.schedulers.background import BackgroundScheduler

from fake_proxy import FakeProxyServer
from service_chaperone.config import load_config
from service_chaperone.connectivity import Connectivity
from service_chaperone.engine import Engine
from service_chaperone.models import ServiceState
from service_chaperone.scheduler import add_monitor_jobs

INTERVAL = 2.0
TIMEOUT = 1.0
RETRIES = 1
DETECTION_BUDGET = (RETRIES + 1) * INTERVAL + TIMEOUT  # 5.0 s


class _OkHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        pass

    def do_GET(self) -> None:
        body = b"ok\n"
        self.send_response(200, "OK")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class _LocalHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def _unused_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class _ToggleableHTTP:
    def __init__(self, port: int) -> None:
        self.port = port
        self._server: _LocalHTTPServer | None = None

    def start(self) -> None:
        self._server = _LocalHTTPServer(("127.0.0.1", self.port), _OkHandler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None


class _ToggleableProxy:
    def __init__(self, port: int) -> None:
        self.port = port
        self._server: FakeProxyServer | None = None

    def start(self) -> None:
        self._server = FakeProxyServer("127.0.0.1", self.port, quiet=True)
        self._server.start_in_background()

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None


class _ToggleablePort:
    def __init__(self, port: int) -> None:
        self.port = port
        self._sock: socket.socket | None = None
        self._stop = threading.Event()

    def start(self) -> None:
        self._stop.clear()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", self.port))
        sock.listen(5)
        sock.settimeout(0.2)
        self._sock = sock

        def _accept_loop() -> None:
            while not self._stop.is_set():
                try:
                    conn, _ = sock.accept()
                    conn.close()
                except TimeoutError:
                    continue
                except OSError:
                    break

        threading.Thread(target=_accept_loop, daemon=True).start()

    def stop(self) -> None:
        self._stop.set()
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None


def _wait_for_event(
    events: list[tuple[str, ServiceState, float]],
    lock: threading.Lock,
    start_index: int,
    target_name: str,
    target_state: ServiceState,
    max_wait: float,
) -> float | None:
    deadline = time.monotonic() + max_wait
    while time.monotonic() < deadline:
        with lock:
            for name, state, ts in events[start_index:]:
                if name == target_name and state is target_state:
                    return ts
        time.sleep(0.05)
    return None


def main() -> int:
    web_port = _unused_port()
    upstream_port = _unused_port()
    proxy_port = _unused_port()
    tcp_port = _unused_port()

    upstream = _ToggleableHTTP(upstream_port)
    website = _ToggleableHTTP(web_port)
    proxy = _ToggleableProxy(proxy_port)
    tcp_service = _ToggleablePort(tcp_port)

    upstream.start()
    website.start()
    proxy.start()
    tcp_service.start()

    config_text = f"""
[[monitor]]
name = "Test website"
type = "website"
url = "http://127.0.0.1:{web_port}/health"
interval = {INTERVAL}
timeout = {TIMEOUT}
retries = {RETRIES}

[[monitor]]
name = "Test proxy"
type = "proxy"
proxy = "http://127.0.0.1:{proxy_port}"
url = "http://127.0.0.1:{upstream_port}/health"
interval = {INTERVAL}
timeout = {TIMEOUT}
retries = {RETRIES}

[[monitor]]
name = "Test port"
type = "port"
host = "127.0.0.1"
port = {tcp_port}
interval = {INTERVAL}
timeout = {TIMEOUT}
retries = {RETRIES}
""".strip() + "\n"

    events: list[tuple[str, ServiceState, float]] = []
    offline_notices: list[str] = []
    events_lock = threading.Lock()
    failures: list[str] = []

    def on_change(monitor, state: ServiceState) -> None:
        with events_lock:
            events.append((monitor.name, state, time.monotonic()))

    def check(label: str, condition: bool, detail: str = "") -> None:
        if condition:
            print(f"[PASS] {label}")
        else:
            msg = f"[FAIL] {label}" + (f" -> {detail}" if detail else "")
            print(msg)
            failures.append(msg)

    scheduler = BackgroundScheduler()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "multi-outage.toml"
            config_path.write_text(config_text)
            monitors = load_config(config_path)

        engine = Engine(
            monitors,
            on_change=on_change,
            connectivity=Connectivity(),
            on_offline=lambda hosts: offline_notices.append(hosts),
        )
        add_monitor_jobs(scheduler, monitors, on_result=engine.handle_result)
        scheduler.start()

        print(
            f"Config: interval={INTERVAL}s, timeout={TIMEOUT}s, retries={RETRIES} "
            f"(DOWN budget = {DETECTION_BUDGET:.1f}s)"
        )
        # Let every monitor complete at least one healthy check first.
        time.sleep(INTERVAL + 0.5)
        with events_lock:
            startup_events = list(events)
        check(
            "Startup quiet while all three services are healthy",
            len(startup_events) == 0,
            f"unexpected startup events: {startup_events!r}",
        )

        targets = [
            ("Test website", website),
            ("Test proxy", proxy),
            ("Test port", tcp_service),
        ]

        for name, service in targets:
            with events_lock:
                phase_start = len(events)

            # Take this service down and measure time to DOWN alert.
            t_down_start = time.monotonic()
            service.stop()
            down_ts = _wait_for_event(
                events,
                events_lock,
                phase_start,
                name,
                ServiceState.DOWN,
                max_wait=DETECTION_BUDGET + 2.0,
            )
            down_elapsed = (down_ts - t_down_start) if down_ts is not None else None

            # Wait one extra interval to confirm no duplicate DOWN alerts fire.
            time.sleep(INTERVAL + 0.5)

            # Bring this service back up and wait for recovery.
            with events_lock:
                recovery_start = len(events)
            t_up_start = time.monotonic()
            service.start()
            up_ts = _wait_for_event(
                events,
                events_lock,
                recovery_start,
                name,
                ServiceState.UP,
                max_wait=DETECTION_BUDGET + 2.0,
            )
            up_elapsed = (up_ts - t_up_start) if up_ts is not None else None

            # Wait one extra interval to confirm no extra alerts fire after recovery.
            time.sleep(INTERVAL + 0.5)

            with events_lock:
                phase_events = events[phase_start:]

            own_downs = [e for e in phase_events if e[0] == name and e[1] is ServiceState.DOWN]
            own_ups = [e for e in phase_events if e[0] == name and e[1] is ServiceState.UP]
            other_events = [e for e in phase_events if e[0] != name]

            within_budget = down_elapsed is not None and down_elapsed <= DETECTION_BUDGET
            summary = (
                f"DOWN in {down_elapsed:.2f}s (budget {DETECTION_BUDGET:.1f}s), "
                f"UP in {up_elapsed:.2f}s"
                if down_elapsed is not None and up_elapsed is not None
                else f"down_elapsed={down_elapsed}, up_elapsed={up_elapsed}"
            )
            check(
                f"{name}: 1 DOWN + 1 recovery within budget, 0 alerts on other services ({summary})",
                len(own_downs) == 1
                and len(own_ups) == 1
                and len(other_events) == 0
                and within_budget,
                f"phase_events={[(n, s.value) for n, s, _ in phase_events]!r}",
            )

        check(
            "Zero offline notifications during loopback outage test",
            len(offline_notices) == 0,
            f"offline_notices={offline_notices!r}",
        )
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)
        website.stop()
        proxy.stop()
        tcp_service.stop()
        upstream.stop()

    print(f"\nFinished with {len(failures)} failure(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())