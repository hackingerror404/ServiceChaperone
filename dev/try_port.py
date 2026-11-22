"""Exercise TCP port check scenarios locally, with no internet required."""

import socket
import sys
import time

from service_chaperone.checks.port import check_port

def _unused_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]

def _make_stalled_listener() -> tuple[socket.socket, list[socket.socket], int]:
    """Bind a socket whose accept queue is full so new connections time out."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(0)
    port = listener.getsockname()[1]

    fillers: list[socket.socket] = []
    for _ in range(16):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(0.1)
        try:
            client.connect(("127.0.0.1", port))
            fillers.append(client)
        except TimeoutError:
            client.close()
            break
    return listener, fillers, port

def run_scenarios() -> int:
    failures: list[str] = []

    def check(label: str, condition: bool, detail: str = "") -> None:
        if condition:
            print(f"[PASS] {label}")
        else:
            msg = f"[FAIL] {label}" + (f" -> {detail}" if detail else "")
            print(msg)
            failures.append(msg)

    # 1. Listening local port -> UP
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        open_port = listener.getsockname()[1]

        res = check_port("127.0.0.1", open_port, timeout=2.0)
        check(
            "Listening local port gives UP with response time",
            res.ok and res.response_ms is not None and res.response_ms >= 0,
            repr(res),
        )

    # 2. Closed local port -> DOWN with "connection refused"
    closed_port = _unused_port()
    res = check_port("127.0.0.1", closed_port, timeout=2.0)
    check(
        "Closed local port gives DOWN with 'connection refused'",
        (not res.ok)
        and res.error is not None
        and "connection refused" in res.error.lower(),
        repr(res),
    )

    # 3. Host that never answers -> DOWN after timeout
    stalled, fillers, stalled_port = _make_stalled_listener()
    try:
        timeout = 0.5
        t0 = time.perf_counter()
        res = check_port("127.0.0.1", stalled_port, timeout=timeout)
        elapsed = time.perf_counter() - t0
        check(
            "Unresponsive port times out within timeout + 1 s",
            (not res.ok)
            and res.error is not None
            and "timed out" in res.error.lower()
            and elapsed <= timeout + 1.0,
            f"elapsed={elapsed:.2f}s, res={res!r}",
        )
    finally:
        for sock in fillers:
            sock.close()
        stalled.close()

    # 4. Unresolvable hostname -> DOWN with readable error, no exception
    res = check_port("nonexistent.invalid", 80, timeout=2.0)
    check(
        "Unresolvable hostname gives DOWN with readable error",
        (not res.ok) and res.error is not None and len(res.error) > 0,
        repr(res),
    )

    print(f"\nFinished with {len(failures)} failure(s).")
    return 1 if failures else 0

if __name__ == "__main__":
    sys.exit(run_scenarios())