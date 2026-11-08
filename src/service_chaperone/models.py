from dataclasses import dataclass
from enum import StrEnum
  
class ServiceState(StrEnum): 
    UP = "up"
    DOWN = "down"
    UNKNOWN = "unknown"  # not checked yet...abs

@dataclass(frozen=True)
class CheckResult:
    ok: bool
    response_ms: float | None = None
    error: str | None = None