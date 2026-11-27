from dataclasses import dataclass, field
from enum import StrEnum

class ServiceState(StrEnum):
    UP = "up"
    DOWN = "down"
    UNKNOWN = "unknown"  # not checked yet

@dataclass(frozen=True)
class CheckResult:
    ok: bool
    response_ms: float | None = None
    error: str | None = None

@dataclass(frozen=True)
class Monitor:
    name: str
    type: str
    url: str | None = None
    interval: float = 60.0
    timeout: float = 10.0
    retries: int = 2
    proxy: str | None = field(default=None, repr=False)
    host: str | None = None
    port: int | None = None

@dataclass(frozen=True)
class Config:
    monitors: tuple[Monitor, ...]
    notify: tuple[str, ...] = field(default=(), repr=False)