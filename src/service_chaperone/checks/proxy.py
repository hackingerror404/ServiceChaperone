from service_chaperone.checks.website import check_website
from service_chaperone.config import DEFAULT_PROXY_TEST_URL, validate_proxy_url
from service_chaperone.models import CheckResult

def check_proxy(
    proxy: str | None,
    url: str | None = None,
    timeout: float = 10.0,
    monitor_name: str = "<proxy>",
) -> CheckResult:
    if not proxy:
        return CheckResult(
            ok=False,
            response_ms=None,
            error=f"Monitor '{monitor_name}' (field 'proxy'): missing proxy URL",
        )
    try:
        validate_proxy_url(proxy, monitor_name)
    except ValueError as exc:
        return CheckResult(ok=False, response_ms=None, error=str(exc))

    target_url = url or DEFAULT_PROXY_TEST_URL
    return check_website(target_url, timeout=timeout, proxy=proxy)