from dataclasses import dataclass

@dataclass(frozen=True)
class CheckResult:
    ok: bool
    response_ms: float | None = None
    error: str | None = None