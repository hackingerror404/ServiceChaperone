"""Exercise connectivity self-check scenarios locally with fake reference hosts."""

import logging
import socket
import sys
import time

from service_chaperone.connectivity import Connectivity, is_loopback_monitor
from service_chaperone.engine import Engine
from service_chaperone.models import CheckResult, Monitor, ServiceState

def _open_listener() -> tuple[socket.socket, int]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    sock.listen(5)
    return sock, sock.getsockname()[1]

def _unused_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]

class _LogCollector(logging.Handler):
    def __init__(self):
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record):
        self.messages.append(self.format(record))

def run_scenarios() -> int:
    failures: list[str] = []

    def check(label: str, condition: bool, detail: str = "") -> None:
        if condition:
            print(f"[PASS] {label}")
        else:
            msg = f"[FAIL] {label}" + (f" -> {detail}" if detail else "")
            print(msg)
            failures.append(msg)

    engine_logger = logging.getLogger("service_chaperone.engine")
    collector = _LogCollector()
    engine_logger.addHandler(collector)
    engine_logger.setLevel(logging.INFO)

    fail_res = CheckResult(ok=False, error="connection error")
    ok_res = CheckResult(ok=True, response_ms=12.0)

    remote_site = Monitor(
        name="Remote site",
        type="website",
        url="https://example.com",
        interval=60,
        timeout=5,
        retries=2,
    )

    try:
        # 1. Both reference hosts unreachable -> 0 DOWN alerts, 1 offline notification naming hosts
        dead1, dead2 = _unused_port(), _unused_port()
        hosts = (("127.0.0.1", dead1), ("127.0.0.1", dead2))
        conn = Connectivity(hosts=hosts, timeout=0.5, cache_ttl=10.0)

        changes: list[tuple[str, ServiceState]] = []
        offline_notices: list[str] = []
        collector.messages.clear()

        engine = Engine(
            [remote_site],
            on_change=lambda m, s: changes.append((m.name, s)),
            connectivity=conn,
            on_offline=lambda h: offline_notices.append(h),
        )
        for _ in range(3):
            engine.handle_result(remote_site, fail_res)

        check(
            "Both hosts unreachable: 3 failures -> 0 DOWN alerts, 1 offline notice",
            len(changes) == 0 and len(offline_notices) == 1,
            f"changes={changes!r}, offline={offline_notices!r}",
        )

        # 6. Offline notification and log both name the unreachable hosts
        expected_a = f"127.0.0.1:{dead1}"
        expected_b = f"127.0.0.1:{dead2}"
        notice_ok = (
            len(offline_notices) == 1
            and expected_a in offline_notices[0]
            and expected_b in offline_notices[0]
        )
        log_ok = any(
            expected_a in msg and expected_b in msg for msg in collector.messages
        )
        check(
            "Offline notification and log both name unreachable reference hosts",
            notice_ok and log_ok,
            f"notices={offline_notices!r}, logs={collector.messages!r}",
        )

        # 2 & 5. Silent recovery resets counts to 0; subsequent outage notifies again
        ref_sock, ref_port = _open_listener()
        try:
            # Start offline (rebindable port: closed first, then opened)
            ref_sock.close()
            dead_extra = _unused_port()
            conn2 = Connectivity(
                hosts=(("127.0.0.1", ref_port), ("127.0.0.1", dead_extra)),
                timeout=0.5,
                cache_ttl=0.1,
            )
            changes.clear()
            offline_notices.clear()
            engine2 = Engine(
                [remote_site],
                on_change=lambda m, s: changes.append((m.name, s)),
                connectivity=conn2,
                on_offline=lambda h: offline_notices.append(h),
            )

            # Episode 1: 4 failures while offline -> still only 1 offline notice, 0 DOWN
            for _ in range(4):
                engine2.handle_result(remote_site, fail_res)
            ep1_ok = len(changes) == 0 and len(offline_notices) == 1

            # Bring one reference host back online and let cache expire
            ref_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ref_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            ref_sock.bind(("127.0.0.1", ref_port))
            ref_sock.listen(5)
            time.sleep(0.15)

            # First failure after restoration should NOT immediately declare DOWN
            # (counts reset to 0, so it needs 3 fresh failures with retries=2)
            engine2.handle_result(remote_site, fail_res)
            not_immediate = len(changes) == 0

            # Failures 2 and 3 while online -> now DOWN
            engine2.handle_result(remote_site, fail_res)
            still_counting = len(changes) == 0
            engine2.handle_result(remote_site, fail_res)
            caught_on_third = changes == [("Remote site", ServiceState.DOWN)]

            check(
                "Connection returns: counts resume from 0, real outage caught on 3rd failure",
                ep1_ok and not_immediate and still_counting and caught_on_third,
                f"ep1={ep1_ok}, changes={changes!r}, offline={offline_notices!r}",
            )

            # Recover the site, then drop connectivity again for Episode 2
            engine2.handle_result(remote_site, ok_res)
            ref_sock.close()
            changes.clear()

            # 3 failures during Episode 2 -> second offline notice fires once
            for _ in range(3):
                engine2.handle_result(remote_site, fail_res)

            check(
                "Second offline episode after silent recovery sends 1 new offline notice",
                len(changes) == 0 and len(offline_notices) == 2,
                f"changes={changes!r}, offline={offline_notices!r}",
            )
        finally:
            ref_sock.close()

        # 3. Only one reference host unreachable -> machine counts as online
        live_sock, live_port = _open_listener()
        try:
            conn_one = Connectivity(
                hosts=(("127.0.0.1", _unused_port()), ("127.0.0.1", live_port)),
                timeout=0.5,
                cache_ttl=10.0,
            )
            changes.clear()
            offline_notices.clear()
            engine3 = Engine(
                [remote_site],
                on_change=lambda m, s: changes.append((m.name, s)),
                connectivity=conn_one,
                on_offline=lambda h: offline_notices.append(h),
            )
            for _ in range(3):
                engine3.handle_result(remote_site, fail_res)

            check(
                "One reference host up, one down -> online, normal DOWN alert fires",
                changes == [("Remote site", ServiceState.DOWN)]
                and len(offline_notices) == 0,
                f"changes={changes!r}, offline={offline_notices!r}",
            )
        finally:
            live_sock.close()

        # 4. Loopback targets never trigger the self-check
        local_site = Monitor(
            name="Local site",
            type="website",
            url="http://127.0.0.1:8000",
            interval=60,
            timeout=5,
            retries=2,
        )
        local_port = Monitor(
            name="Local port",
            type="port",
            host="127.0.0.1",
            port=8000,
            interval=60,
            timeout=5,
            retries=2,
        )
        local_proxy_remote_target = Monitor(
            name="Local proxy to internet",
            type="proxy",
            proxy="http://127.0.0.1:3128",
            url="https://example.com",
            interval=60,
            timeout=5,
            retries=2,
        )

        class _ExplodingConnectivity(Connectivity):
            def is_online(self) -> bool:
                raise AssertionError("Self-check should not run for loopback targets")

        changes.clear()
        offline_notices.clear()
        engine4 = Engine(
            [local_site, local_port],
            on_change=lambda m, s: changes.append((m.name, s)),
            connectivity=_ExplodingConnectivity(),
            on_offline=lambda h: offline_notices.append(h),
        )
        for _ in range(3):
            engine4.handle_result(local_site, fail_res)
            engine4.handle_result(local_port, fail_res)

        check(
            "Loopback targets never trigger self-check (local proxy->remote still does)",
            len(changes) == 2
            and len(offline_notices) == 0
            and not is_loopback_monitor(local_proxy_remote_target),
            f"changes={changes!r}",
        )
    finally:
        engine_logger.removeHandler(collector)

    print(f"\nFinished with {len(failures)} failure(s).")
    return 1 if failures else 0

if __name__ == "__main__":
    sys.exit(run_scenarios())