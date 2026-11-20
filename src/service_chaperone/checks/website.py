import time
from importlib.metadata import PackageNotFoundError, version

import httpx

from service_chaperone.config import redact_url
from service_chaperone.models import CheckResult

try:
    _VERSION = version("service-chaperone")
except PackageNotFoundError:
    _VERSION = "unknown"

_HEADERS = {"User-Agent": f"service-chaperone/{_VERSION}"}

def _scrub_credentials(text: str) -> str:
    parts: list[str] = []
    for token in text.split():
        if "://" in token and "@" in token:
            parts.append(redact_url(token))
        else:
            parts.append(token)
    return " ".join(parts)

def check_website(
    url: str,
    timeout: float = 10.0,
    *,
    proxy: str | None = None,
) -> CheckResult:
    """Check an HTTP(S) endpoint, optionally routed through an HTTP(S) proxy."""
    start = time.perf_counter()
    client_kwargs: dict = {
        "timeout": timeout,
        "follow_redirects": True,
        "trust_env": False,
        "headers": _HEADERS,
    }
    if proxy is not None:
        client_kwargs["proxy"] = proxy

    try:
        with httpx.Client(**client_kwargs) as client:
            response = client.get(url)
        response_ms = round((time.perf_counter() - start) * 1000.0, 1)
        if 200 <= response.status_code < 400:
            return CheckResult(ok=True, response_ms=response_ms)
        reason = response.reason_phrase or ""
        detail = f"HTTP {response.status_code} {reason}".strip()
        return CheckResult(ok=False, response_ms=response_ms, error=detail)
    except httpx.TimeoutException:
        response_ms = round((time.perf_counter() - start) * 1000.0, 1)
        target = f"proxy {redact_url(proxy)}" if proxy else url
        return CheckResult(
            ok=False,
            response_ms=response_ms,
            error=f"timed out checking {target}",
        )
    except httpx.ProxyError as exc:
        response_ms = round((time.perf_counter() - start) * 1000.0, 1)
        safe_proxy = redact_url(proxy) if proxy else "<proxy>"
        detail = _scrub_credentials(str(exc))
        return CheckResult(
            ok=False,
            response_ms=response_ms,
            error=f"proxy error ({safe_proxy}): {detail}",
        )
    except httpx.ConnectError as exc:
        response_ms = round((time.perf_counter() - start) * 1000.0, 1)
        if proxy is not None:
            return CheckResult(
                ok=False,
                response_ms=response_ms,
                error=f"could not connect to the proxy ({redact_url(proxy)})",
            )
        return CheckResult(
            ok=False,
            response_ms=response_ms,
            error=f"connection error: {_scrub_credentials(str(exc))}",
        )
    except httpx.HTTPError as exc:
        response_ms = round((time.perf_counter() - start) * 1000.0, 1)
        return CheckResult(
            ok=False,
            response_ms=response_ms,
            error=f"request error: {_scrub_credentials(str(exc))}",
        )