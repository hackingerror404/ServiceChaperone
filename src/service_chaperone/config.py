import math
import os
import tomllib
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from service_chaperone.models import Monitor

DEFAULT_INTERVAL = 60  # seconds between checks
DEFAULT_TIMEOUT = 10  # seconds before a check counts as failed
DEFAULT_RETRIES = 2  # extra failures allowed before a service is called down

SUPPORTED_TYPES = ("website", "proxy", "port")
PLANNED_TYPES: tuple[str, ...] = ()

_BASE_REQUIRED_FIELDS = ("name", "type")
_OPTIONAL_FIELDS = ("url", "proxy", "host", "port", "interval", "timeout", "retries")
_ALL_FIELDS = _BASE_REQUIRED_FIELDS + _OPTIONAL_FIELDS

DEFAULT_PROXY_TEST_URL = "https://example.com"
SUPPORTED_PROXY_SCHEMES = {"http", "https"}

class ConfigError(Exception):
    def __init__(self, problems):
        if isinstance(problems, str):
            problems = [problems]
        self.problems = list(problems)
        super().__init__("\n".join(self.problems))

def default_config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) if base and os.path.isabs(base) else Path.home() / ".config"
    return root / "service-chaperone" / "config.toml"

def load_config(path=None) -> list[Monitor]:
    path = Path(path) if path is not None else default_config_path()
    data = _read_toml(path)

    raw_monitors = data.get("monitor")
    if raw_monitors is None or raw_monitors == []:
        raise ConfigError(
            f"{path}: no monitors found. Add at least one [[monitor]] block; "
            f"see config.example.toml"
        )
    if not isinstance(raw_monitors, list):
        raise ConfigError(
            f"{path}: write each monitor as [[monitor]] with double brackets"
        )

    monitors: list[Monitor] = []
    problems: list[str] = []
    for index, raw in enumerate(raw_monitors, start=1):
        monitor, found = _validate_monitor(raw, index)
        problems.extend(found)
        if monitor is not None:
            monitors.append(monitor)

    if problems:
        raise ConfigError(problems)
    return monitors

def redact_url(raw_url: str) -> str:
    try:
        parsed = urlparse(raw_url)
    except ValueError:
        return "<redacted-url>"
    if not parsed.scheme:
        return "<invalid-url>"
    host = parsed.hostname or ""
    netloc = f"{host}:{parsed.port}" if parsed.port else host
    return urlunparse((parsed.scheme, netloc, parsed.path or "", "", "", ""))

def validate_proxy_url(raw_proxy: str, monitor_name: str) -> str:
    parsed = urlparse(raw_proxy)
    scheme = (parsed.scheme or "").lower()
    if scheme.startswith("socks"):
        raise ValueError(
            f"Monitor '{monitor_name}' (field 'proxy'): SOCKS proxies are not supported yet."
        )
    if scheme not in SUPPORTED_PROXY_SCHEMES or not parsed.hostname:
        safe_url = redact_url(raw_proxy)
        raise ValueError(
            f"Monitor '{monitor_name}' (field 'proxy'): expected an http:// or https:// URL with a host, got '{safe_url}'."
        )
    return raw_proxy

def _read_toml(path: Path) -> dict:
    try:
        with open(path, "rb") as file:  # tomllib needs binary mode
            return tomllib.load(file)
    except FileNotFoundError:
        raise ConfigError(
            f"config file not found: {path}\n"
            "Copy config.example.toml there and edit it."
        ) from None
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path} is not valid TOML: {exc}") from None
    except OSError as exc:
        raise ConfigError(f"could not read {path}: {exc.strerror or exc}") from None

def _make_label(raw, index: int) -> str:
    name = raw.get("name") if isinstance(raw, dict) else None
    if isinstance(name, str) and name.strip():
        return f"monitor '{name.strip()}'"
    return f"monitor #{index}"

def _validate_monitor(raw, index: int):
    label = _make_label(raw, index)
    problems: list[str] = []

    if not isinstance(raw, dict):
        problems.append(f"{label}: each [[monitor]] entry must be a table")
        return None, problems

    for key in raw:
        if key not in _ALL_FIELDS:
            problems.append(f"{label}: unknown field '{key}'")

    for field in _BASE_REQUIRED_FIELDS:
        if field not in raw:
            problems.append(f"{label}: missing required field '{field}'")

    if "name" in raw and not (isinstance(raw["name"], str) and raw["name"].strip()):
        problems.append(f"{label}: 'name' must be non-empty text (got {raw['name']!r})")

    name = raw["name"].strip() if isinstance(raw.get("name"), str) and raw["name"].strip() else None

    type_var = raw.get("type")
    type_valid = False
    if "type" in raw:
        if type_var in PLANNED_TYPES:
            problems.append(
                f"{label}: type '{type_var}' is not supported yet "
                f"(supported now: {', '.join(SUPPORTED_TYPES)})"
            )
        elif type_var not in SUPPORTED_TYPES:
            problems.append(
                f"{label}: unknown type {type_var!r} "
                f"(supported: {', '.join(SUPPORTED_TYPES)})"
            )
        else:
            type_valid = True

    has_url = "url" in raw
    url_raw = raw.get("url")
    url: str | None = None
    if has_url:
        if not (isinstance(url_raw, str) and url_raw.strip()):
            problems.append(f"{label}: 'url' must be non-empty text (got {url_raw!r})")
        else:
            url = url_raw.strip()

    has_proxy = "proxy" in raw
    proxy_raw = raw.get("proxy")
    proxy: str | None = None
    if has_proxy:
        if not (isinstance(proxy_raw, str) and proxy_raw.strip()):
            problems.append(
                f"{label}: 'proxy' must be non-empty text (field 'proxy')"
            )
        else:
            proxy = proxy_raw.strip()

    has_host = "host" in raw
    host_raw = raw.get("host")
    host: str | None = None
    if has_host:
        if not (isinstance(host_raw, str) and host_raw.strip()):
            problems.append(f"{label}: 'host' must be non-empty text (got {host_raw!r})")
        elif "://" in host_raw:
            problems.append(
                f"{label}: 'host' should be a hostname or IP address, not a URL (got {host_raw!r})"
            )
        else:
            host = host_raw.strip()

    has_port = "port" in raw
    port = _get_port(raw, label, problems)

    if type_valid and type_var == "website":
        if not has_url:
            problems.append(f"{label}: missing required field 'url' for website monitor")
        for forbidden in ("proxy", "host", "port"):
            if forbidden in raw:
                problems.append(
                    f"{label}: '{forbidden}' is not allowed for website monitors (field '{forbidden}')"
                )

    elif type_valid and type_var == "proxy":
        if not has_proxy:
            problems.append(f"{label}: missing required field 'proxy' for proxy monitor")
        elif proxy is not None:
            try:
                validate_proxy_url(proxy, name or label)
            except ValueError as exc:
                problems.append(str(exc))
        for forbidden in ("host", "port"):
            if forbidden in raw:
                problems.append(
                    f"{label}: '{forbidden}' is not allowed for proxy monitors (field '{forbidden}')"
                )
        if not has_url:
            url = DEFAULT_PROXY_TEST_URL

    elif type_valid and type_var == "port":
        if not has_host:
            problems.append(f"{label}: missing required field 'host' for port monitor")
        if not has_port:
            problems.append(f"{label}: missing required field 'port' for port monitor")
        for forbidden in ("url", "proxy"):
            if forbidden in raw:
                problems.append(
                    f"{label}: '{forbidden}' is not allowed for port monitors (field '{forbidden}')"
                )

    interval = _check_number_range(raw, "interval", DEFAULT_INTERVAL, label, problems)
    timeout = _check_number_range(raw, "timeout", DEFAULT_TIMEOUT, label, problems)
    retries = _get_retry_count(raw, label, problems)

    if problems or name is None or type_var is None:
        return None, problems

    monitor = Monitor(
        name=name,
        type=type_var,
        url=url,
        proxy=proxy,
        host=host,
        port=port,
        interval=interval,
        timeout=timeout,
        retries=retries,
    )
    return monitor, []

def _get_port(raw, label, problems):
    if "port" not in raw:
        return None
    value = raw["port"]
    if isinstance(value, bool) or not isinstance(value, int) or not (1 <= value <= 65535):
        problems.append(
            f"{label}: 'port' must be a whole number between 1 and 65535 (got {value!r})"
        )
        return None
    return value

def _check_number_range(raw, field, default, label, problems):
    if field not in raw:
        return float(default)
    value = raw[field]
    try:
        seconds = float(value) if isinstance(value, (int, float)) else None
    except OverflowError:  # an integer too big to be a float
        seconds = None
    if seconds is None or not math.isfinite(seconds) or seconds <= 0:
        problems.append(f"{label}: '{field}' must be a number greater than 0 (got {value!r})")
        return None
    return seconds

def _get_retry_count(raw, label, problems):
    if "retries" not in raw:
        return DEFAULT_RETRIES
    value = raw["retries"]
    if not isinstance(value, int) or value < 0:
        problems.append(f"{label}: 'retries' must be a whole number, 0 or more (got {value!r})")
        return None
    return value