import math
import os
import tomllib
from pathlib import Path

from service_chaperone.models import Monitor

DEFAULT_INTERVAL = 60  # seconds between checks
DEFAULT_TIMEOUT = 10  # seconds before a check counts as failed
DEFAULT_RETRIES = 2  # extra failures allowed before a service is called down

SUPPORTED_TYPES = ("website",)
PLANNED_TYPES = ("proxy", "port")  # recognised, but not built yet

_REQUIRED_FIELDS = ("name", "type", "url")
_OPTIONAL_FIELDS = ("interval", "timeout", "retries")
_ALL_FIELDS = _REQUIRED_FIELDS + _OPTIONAL_FIELDS

class ConfigError(Exception):
    """The config file can't be used. str(error) lists every problem found."""

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

    for key in raw:
        if key not in _ALL_FIELDS:
            problems.append(f"{label}: unknown field '{key}'")

    for field in _REQUIRED_FIELDS:
        if field not in raw:
            problems.append(f"{label}: missing required field '{field}'")

    for field in ("name", "url"):
        if field in raw and not (isinstance(raw[field], str) and raw[field].strip()):
            problems.append(f"{label}: '{field}' must be non-empty text (got {raw[field]!r})")

    name = raw.get("name")

    type_var = raw.get("type")
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

    url = raw.get("url")

    interval = _check_number_range(raw, "interval", DEFAULT_INTERVAL, label, problems)
    timeout = _check_number_range(raw, "timeout", DEFAULT_TIMEOUT, label, problems)
    retries = _get_retry_count(raw, label, problems)

    if problems:
        return None, problems
    monitor = Monitor(
        name=name.strip(),
        type=type_var,
        url=url,
        interval=interval,
        timeout=timeout,
        retries=retries,
    )
    return monitor, []

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