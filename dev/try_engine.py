"""Check the engine's up/down rules with made-up results and report PASS or FAIL.

This is a development tool made with Claude. It is not part of the installed package.

    python dev/try_engine.py

No network and no server are needed: results are fed in by hand and alerts are
recorded in a list instead of showing popups. The script exits with status 1 if
anything fails, so you can paste its output into a PR.

In the sequences below, S is a successful check and F is a failed one.
"""

import logging
import sys
import threading

from service_chaperone.engine import Engine
from service_chaperone.models import CheckResult, Monitor, ServiceState

UP, DOWN = ServiceState.UP, ServiceState.DOWN
OK = CheckResult(ok=True, response_ms=10.0)
FAIL = CheckResult(ok=False, error="boom")

results = []  # (passed, description)

# The engine logs every state change. Collect those lines here for the whole
# run, so they don't flood the screen (the stress test below makes thousands).
engine_log = []


class Grab(logging.Handler):
    def emit(self, record):
        engine_log.append(record.getMessage())


_logger = logging.getLogger("service_chaperone.engine")
_logger.addHandler(Grab())
_logger.setLevel(logging.INFO)
_logger.propagate = False


def check(passed: bool, description: str, detail: str = "") -> None:
    results.append(passed)
    print(f"{'PASS' if passed else 'FAIL'}  {description}")
    if not passed and detail:
        print(f"      {detail}")


def monitor(name="Site", url="https://example.com", retries=2) -> Monitor:
    return Monitor(name, "website", url, 60.0, 10.0, retries)


def run_sequence(sequence: str, retries: int = 2):
    """Feed S/F results to one monitor. Returns [(position, new state), ...],
    where position counts from 1 and says which result caused the alert."""
    alerts = []
    current = {"position": 0}
    m = monitor(retries=retries)
    engine = Engine([m], lambda mon, state: alerts.append((current["position"], state)))
    for position, letter in enumerate(sequence, start=1):
        current["position"] = position
        engine.handle_result(m, OK if letter == "S" else FAIL)
    return alerts


# (description, sequence, retries, expected alerts)
SEQUENCES = [
    ("two failures then a success (retries 2): no alert", "FFS", 2, []),
    ("...and the count reset: two more failures are still quiet", "FFSFF", 2, []),
    ("...but a third failure after the reset does alert", "FFSFFF", 2, [(6, DOWN)]),
    ("three failures in a row: exactly one DOWN, on the third", "FFF", 2, [(3, DOWN)]),
    ("more failures while already DOWN: no more alerts", "FFFFFFFF", 2, [(3, DOWN)]),
    ("first success after DOWN: exactly one recovered", "FFFS", 2, [(3, DOWN), (4, UP)]),
    ("...and further successes stay quiet", "FFFSSSS", 2, [(3, DOWN), (4, UP)]),
    ("healthy from the start: never any alert", "SSSSS", 2, []),
    ("a service already down at startup still alerts", "FFFF", 2, [(3, DOWN)]),
    ("retries = 0: the first failure is DOWN", "FS", 0, [(1, DOWN), (2, UP)]),
    ("retries = 1: DOWN on the second failure", "FFSFF", 1, [(2, DOWN), (3, UP), (5, DOWN)]),
    ("a flapping service alerts once per change",
     "FFFSFFFS", 2, [(3, DOWN), (4, UP), (7, DOWN), (8, UP)]),
]


def main() -> int:
    for description, sequence, retries, expected in SEQUENCES:
        got = run_sequence(sequence, retries)
        check(got == expected, f"{description}   [{sequence}]", f"expected {expected}, got {got}")

    # Two monitors failing at the same moment: one alert each.
    alerts = []
    a, b = monitor("Site A", "https://a.example"), monitor("Site B", "https://b.example")
    engine = Engine([a, b], lambda m, s: alerts.append((m.name, s)))
    for _ in range(3):  # both fail together, check by check
        engine.handle_result(a, FAIL)
        engine.handle_result(b, FAIL)
    check(sorted(alerts, key=str) == [("Site A", DOWN), ("Site B", DOWN)],
          "two sites failing at the same moment: one separate DOWN alert each", f"got {alerts}")
    alerts.clear()
    engine.handle_result(a, OK)
    engine.handle_result(b, OK)
    check(sorted(alerts, key=str) == [("Site A", UP), ("Site B", UP)],
          "...and one separate recovered alert each", f"got {alerts}")

    # Only one of two failing.
    alerts = []
    engine = Engine([a, b], lambda m, s: alerts.append((m.name, s)))
    for _ in range(5):
        engine.handle_result(a, FAIL)
        engine.handle_result(b, OK)
    check(alerts == [("Site A", DOWN)], "one failing site does not affect the other", f"got {alerts}")

    # Same name, different URLs: independent state.
    alerts = []
    x, y = monitor("Site", "https://one.example"), monitor("Site", "https://two.example")
    engine = Engine([x, y], lambda m, s: alerts.append((m.url, s)))
    for _ in range(3):
        engine.handle_result(x, FAIL)
        engine.handle_result(y, OK)
    check(alerts == [("https://one.example", DOWN)],
          "two monitors sharing a name keep separate state", f"got {alerts}")

    # An alert that fails must not cause a repeat.
    calls = []
    def flaky(m, s):
        calls.append(s)
        if len(calls) == 1:
            raise RuntimeError("the notifier broke")
    m = monitor()
    engine = Engine([m], flaky)
    raised = False
    try:
        for _ in range(3):
            engine.handle_result(m, FAIL)
    except RuntimeError:
        raised = True
    for _ in range(4):
        engine.handle_result(m, FAIL)  # still down: must stay quiet
    engine.handle_result(m, OK)
    check(raised and calls == [DOWN, UP],
          "a failing alert is not repeated, and the later recovery still arrives",
          f"raised={raised}, alert calls={calls}")

    # State changes are logged.
    engine_log.clear()
    run_sequence("FFFS")
    records = list(engine_log)
    check(any("now DOWN after 3 failure" in r and "Site" in r and "boom" in r for r in records)
          and any("has recovered" in r for r in records) and len(records) == 2,
          "each state change is logged once, with the name, count, and reason", f"got {records}")

    # Many threads at once, as the scheduler runs them.
    monitors = [monitor(f"Site {i}", f"https://{i}.example") for i in range(8)]
    per_monitor = {m: [] for m in monitors}
    engine = Engine(monitors, lambda m, s: per_monitor[m].append(s))
    start = threading.Barrier(len(monitors))
    def hammer(m):
        start.wait()
        for _ in range(250):
            for letter in "FFFS":
                engine.handle_result(m, OK if letter == "S" else FAIL)
    threads = [threading.Thread(target=hammer, args=(m,)) for m in monitors]
    for t in threads: t.start()
    for t in threads: t.join()
    check(all(per_monitor[m] == [DOWN, UP] * 250 for m in monitors),
          "8 monitors hammered from 8 threads at once: every alert exactly right",
          "alerts were wrong or out of order for at least one monitor")

    failed = results.count(False)
    print(f"\n{len(results) - failed} of {len(results)} checks passed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())