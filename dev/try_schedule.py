"""Check the scheduler against the local fake server and report PASS or FAIL.

This is a development tool made by Claude. It is not part of the installed package.

First start the fake server in another terminal:   python dev/fake_server.py
Then run (takes about a minute):                   python dev/try_schedule.py

    python dev/try_schedule.py --seconds 20        # a quicker run

It checks the acceptance criteria of the scheduler issue:
  * one job per monitor, with the right interval
  * checks happen at about the right rate (one log line per check)
  * a monitor that hangs does not delay the others
  * a crash inside one check is logged and the schedule keeps running
  * Ctrl-C stops `service-chaperone run` cleanly, with no traceback
The script exits with status 1 if anything fails.
"""

import argparse
import logging
import signal
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

import httpx
from apscheduler.schedulers.background import BackgroundScheduler

from service_chaperone.models import Monitor
from service_chaperone.scheduler import add_monitor_jobs

BASE = "http://127.0.0.1:8765"

results = []  # (passed, description, detail)


def check(passed: bool, description: str, detail: str = "") -> None:
    results.append((passed, description, detail))
    print(f"{'PASS' if passed else 'FAIL'}  {description}")
    if detail:
        print(f"      {detail}")


class Capture(logging.Handler):
    """Keeps log records in a list instead of printing them."""

    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


def server_is_up() -> bool:
    try:
        return httpx.get(f"{BASE}/ok", timeout=2).status_code == 200
    except httpx.HTTPError:
        return False


def expected_checks(seconds: float, interval: float) -> int:
    # About one check per interval. The first happens immediately and the one
    # due right at the end may not have finished yet, so the real count can be
    # one either side of this (the checks below allow for that).
    return int(seconds // interval)


def scheduler_run(seconds: float) -> None:
    monitors = [
        Monitor("fast", "website", f"{BASE}/ok", 5.0, 3.0, 2),
        Monitor("slower", "website", f"{BASE}/ok", 10.0, 3.0, 2),
        Monitor("hangs", "website", f"{BASE}/slow", 5.0, 8.0, 2),  # hangs longer than its own interval
        Monitor("crashy", "website", f"{BASE}/ok", 5.0, 3.0, 2),
    ]

    times = defaultdict(list)  # monitor name -> times its checks finished
    statuses = defaultdict(list)  # monitor name -> ok or not, per check
    crashed = set()

    def on_result(monitor, result):
        times[monitor.name].append(time.monotonic())
        statuses[monitor.name].append(result.ok)
        if monitor.name == "crashy" and monitor.name not in crashed:
            crashed.add(monitor.name)
            raise RuntimeError("deliberate failure from try_schedule.py")

    capture = Capture()
    root = logging.getLogger()
    root.addHandler(capture)
    root.setLevel(logging.INFO)
    for noisy in ("httpx", "httpcore", "apscheduler"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    scheduler = BackgroundScheduler()
    add_monitor_jobs(scheduler, monitors, on_result)

    # One job per monitor, with the right interval (before anything runs).
    jobs = scheduler.get_jobs()
    intervals = {job.name: job.trigger.interval.total_seconds() for job in jobs}
    wanted = {m.name: m.interval for m in monitors}
    check(
        len(jobs) == len(monitors) and intervals == wanted,
        "one job per monitor, each with its monitor's interval",
        f"jobs: {intervals}",
    )

    print(f"\n  ...running {len(monitors)} monitors for {seconds:.0f} seconds...\n")
    scheduler.start()
    time.sleep(seconds)
    scheduler.shutdown(wait=False)
    root.removeHandler(capture)

    # Rate of checks.
    for name in ("fast", "slower"):
        interval = wanted[name]
        want, got = expected_checks(seconds, interval), len(times[name])
        check(
            abs(got - want) <= 1,
            f"'{name}' (every {interval:.0f} s) was checked about {want} times",
            f"checked {got} times",
        )

    # A hanging monitor must not delay the others.
    gaps = [b - a for a, b in zip(times["fast"], times["fast"][1:])]
    worst = max(gaps) if gaps else float("inf")
    check(
        worst <= wanted["fast"] + 1.5,
        "a monitor that hangs does not delay the others",
        f"'fast' (every 5 s) had a longest gap of {worst:.1f} s while 'hangs' was timing out",
    )
    check(
        bool(statuses["hangs"]) and not any(statuses["hangs"]),
        "the hanging monitor itself is reported DOWN",
        f"{len(statuses['hangs'])} checks, all DOWN" if statuses["hangs"] else "no checks ran",
    )

    # One log line per check.
    for name in ("fast", "slower", "hangs"):
        lines = [r for r in capture.records if r.getMessage().startswith(f"{name}: ")]
        check(
            len(lines) == len(times[name]),
            f"'{name}': exactly one log line per check",
            f"{len(times[name])} checks, {len(lines)} log lines",
        )

    # A crash is logged, and the schedule keeps running.
    crash_logs = [
        r for r in capture.records
        if r.levelno == logging.ERROR and "crashy" in r.getMessage()
    ]
    check(len(crash_logs) == 1, "a crash inside one check is logged", f"{len(crash_logs)} error log(s)")
    check(
        len(times["crashy"]) >= expected_checks(seconds, 5.0) - 1,
        "...and that monitor keeps being checked afterwards",
        f"'crashy' was checked {len(times['crashy'])} times",
    )


def command_run(tmp: Path) -> None:
    config = tmp / "config.toml"
    config.write_text(
        '[[monitor]]\nname = "Home page"\ntype = "website"\n'
        f'url = "{BASE}/ok"\ninterval = 2\ntimeout = 3\n'
    )
    code = (
        "import sys; from service_chaperone.cli import main; "
        "sys.exit(main(['run', '--config', sys.argv[1]]))"
    )
    proc = subprocess.Popen(
        [sys.executable, "-c", code, str(config)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    time.sleep(5)
    proc.send_signal(signal.SIGINT)  # what Ctrl-C does
    try:
        _, err = proc.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
        check(False, "Ctrl-C stops `run` cleanly", "it did not stop within 30 seconds")
        return
    check(
        proc.returncode == 0 and "Traceback" not in err,
        "Ctrl-C stops `run` cleanly: exit status 0, no traceback",
        f"exit status {proc.returncode}, traceback in output: {'Traceback' in err}",
    )
    check(err.count("Home page: UP") >= 2, "`run` prints one log line per check", f"{err.count('Home page: UP')} lines seen")

    missing = subprocess.run(
        [sys.executable, "-c", code, str(tmp / "nope.toml")],
        capture_output=True, text=True,
    )
    check(
        missing.returncode == 1 and "Traceback" not in missing.stderr and "not found" in missing.stderr,
        "`run` with a missing config file: a clear message, exit status 1, no traceback",
        missing.stderr.strip().splitlines()[0] if missing.stderr.strip() else "no output",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--seconds", type=float, default=60, help="how long to watch (default 60)")
    args = parser.parse_args()

    if not server_is_up():
        print(f"The fake server is not running at {BASE}.")
        print("Start it in another terminal with:  python dev/fake_server.py")
        return 2

    scheduler_run(args.seconds)
    print()
    with tempfile.TemporaryDirectory() as tmp:
        command_run(Path(tmp))

    failed = [r for r in results if not r[0]]
    print(f"\n{len(results) - len(failed)} of {len(results)} checks passed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())