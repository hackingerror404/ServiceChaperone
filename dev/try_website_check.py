"""Run check_website against a set of scenarios and report PASS or FAIL.

This is a development tool built with Claude. It is not part of the installed package.

First start the fake server in another terminal:   python dev/fake_server.py
Then run:                                          python dev/try_website_check.py

Each scenario says what the result should look like. The script exits with
status 1 if any scenario does not match, so you can paste its output into a PR
as evidence of how the change was tested.
"""

import sys
import time

from service_chaperone.checks.website import check_website

BASE = "http://127.0.0.1:8765"
TIMEOUT = 3  # seconds

# (name, url, should be ok, text the error must contain, max seconds allowed)
SCENARIOS = [
    ("healthy site", f"{BASE}/ok", True, None, 2),
    ("follows a redirect", f"{BASE}/redirect", True, None, 2),
    ("server error (500)", f"{BASE}/error", False, "500", 2),
    ("never answers", f"{BASE}/slow", False, "timed out", TIMEOUT + 1),
    ("connection refused", "http://127.0.0.1:9", False, "refused", 2),
    ("unresolvable hostname", "http://does-not-exist.invalid", False, "not known", 5),
]

def judge(result, elapsed, expect_ok, error_text, max_seconds):
    """Return a list of problems; an empty list means the scenario passed."""
    problems = []
    if result.ok != expect_ok:
        problems.append(f"expected ok={expect_ok}, got ok={result.ok}")
    if expect_ok and result.response_ms is None:
        problems.append("ok result has no response_ms")
    if expect_ok and result.error is not None:
        problems.append(f"ok result has an error: {result.error}")
    if error_text and (result.error is None or error_text.lower() not in result.error.lower()):
        problems.append(f"error should mention {error_text!r}, got {result.error!r}")
    if elapsed > max_seconds:
        problems.append(f"took {elapsed:.1f}s, limit is {max_seconds}s")
    return problems

def main() -> int:
    failures = 0
    for name, url, expect_ok, error_text, max_seconds in SCENARIOS:
        start = time.perf_counter()
        try:
            result = check_website(url, timeout=TIMEOUT)
        except Exception as exc:  # check_website must never raise
            print(f"FAIL  {name}: raised {type(exc).__name__}: {exc}")
            failures += 1
            continue
        elapsed = time.perf_counter() - start

        problems = judge(result, elapsed, expect_ok, error_text, max_seconds)
        verdict = "PASS" if not problems else "FAIL"
        print(f"{verdict}  {name}")
        print(f"      url:     {url}")
        print(f"      result:  ok={result.ok} response_ms={result.response_ms} error={result.error!r}")
        print(f"      elapsed: {elapsed:.2f}s")
        for problem in problems:
            print(f"      PROBLEM: {problem}")
        failures += bool(problems)

    total = len(SCENARIOS)
    print(f"\n{total - failures} of {total} scenarios passed.")
    return 1 if failures else 0

if __name__ == "__main__":
    sys.exit(main())