import socket
import ssl
import time 
import httpx
from importlib.metadata import PackageNotFoundError, version
 
from service_chaperone.models import CheckResult

# Below settings are necessary for httpx headers to work as needed.
try:
    _VERSION = version("service-chaperone")
except PackageNotFoundError:
    _VERSION = "unknown"
_HEADERS = {"User-Agent": f"service-chaperone/{_VERSION}"}

def check_website(url: str, timeout: float = 10.0) -> CheckResult:
    start = time.perf_counter()
    try:
        with httpx.Client(
            timeout=timeout, follow_redirects=True, headers=_HEADERS
        ) as client:
            response = client.get(url)
    except httpx.TimeoutException:
        return CheckResult(ok=False, error=f"timed out after {timeout:g}s")
    except httpx.TooManyRedirects:
        return CheckResult(ok=False, error="too many redirects")
    except httpx.ConnectError as exc:
        return CheckResult(ok=False, error=f"connection error: {exc}")
    except (httpx.InvalidURL, httpx.UnsupportedProtocol) as exc:
        return CheckResult(ok=False, error=f"invalid URL: {exc}")
    except httpx.HTTPError as exc:
        return CheckResult(ok=False, error=f"request failed: {exc}")
    except Exception as exc:
        return CheckResult(
            ok=False, error=f"unexpected error: {type(exc).__name__}: {exc}"
        )
 
    response_ms = round((time.perf_counter() - start) * 1000, 1)
    status = response.status_code
    if 200 <= status < 400:
        return CheckResult(ok=True, response_ms=response_ms)
    return CheckResult(
        ok=False,
        response_ms=response_ms,
        error=f"HTTP {status} {response.reason_phrase}".strip(),
    )
