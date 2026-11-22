import socket
import time

from service_chaperone.models import CheckResult

def check_port(host: str, port: int, timeout: float = 10.0) -> CheckResult:
    start = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
        response_ms = round((time.perf_counter() - start) * 1000.0, 1)
        return CheckResult(ok=True, response_ms=response_ms)
    except TimeoutError:
        response_ms = round((time.perf_counter() - start) * 1000.0, 1)
        return CheckResult(
            ok=False,
            response_ms=response_ms,
            error=f"timed out connecting to {host}:{port}",
        )
    except ConnectionRefusedError:
        response_ms = round((time.perf_counter() - start) * 1000.0, 1)
        return CheckResult(
            ok=False,
            response_ms=response_ms,
            error=f"connection refused ({host}:{port})",
        )
    except socket.gaierror as exc:
        response_ms = round((time.perf_counter() - start) * 1000.0, 1)
        return CheckResult(
            ok=False,
            response_ms=response_ms,
            error=f"could not resolve host {host!r}: {exc.strerror or exc}",
        )
    except OSError as exc:
        response_ms = round((time.perf_counter() - start) * 1000.0, 1)
        return CheckResult(
            ok=False,
            response_ms=response_ms,
            error=f"connection error ({host}:{port}): {exc.strerror or exc}",
        )