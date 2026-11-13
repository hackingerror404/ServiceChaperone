"""Run load_config against good and bad config files and report PASS or FAIL.

This is a development tool built with Claude. It is not part of the installed package.

    python dev/try_config.py

Each case writes a small TOML file, loads it, and checks the outcome. For bad
files, the error message is printed so you can judge whether it is readable.
The script exits with status 1 if any case does not behave as expected, so you
can paste its output into a PR as evidence of how the change was tested.
"""

import os
import sys
import tempfile
from pathlib import Path

from service_chaperone.config import ConfigError, default_config_path, load_config
from service_chaperone.models import Monitor

REPO_ROOT = Path(__file__).resolve().parent.parent

HEADER = 'name = "Site"\ntype = "website"\nurl = "https://example.com"\n'


def block(extra: str = "", base: str = HEADER) -> str:
    return "[[monitor]]\n" + base + extra


def expect_values(monitors):
    """Checker for the 'two monitors, every field' case."""
    want = [
        Monitor("My website", "website", "https://example.com", 30.0, 5.0, 1),
        Monitor("Home page", "website", "http://127.0.0.1:8765/ok", 120.0, 15.0, 0),
    ]
    return monitors == want or f"got {monitors!r}"


def expect_defaults(monitors):
    want = [Monitor("Site", "website", "https://example.com", 60.0, 10.0, 2)]
    return monitors == want or f"got {monitors!r}"


GOOD_CASES = [
    (
        "two monitors, every field set",
        block('interval = 30\ntimeout = 5\nretries = 1\n', HEADER.replace("Site", "My website"))
        + "\n"
        + '[[monitor]]\nname = "Home page"\ntype = "website"\n'
        'url = "http://127.0.0.1:8765/ok"\ninterval = 120\ntimeout = 15\nretries = 0\n',
        expect_values,
    ),
    ("only required fields get the defaults", block(), expect_defaults),
]

# (name, toml text, substrings the error message must contain)
BAD_CASES = [
    ("missing url", '[[monitor]]\nname = "Site"\ntype = "website"\n', ["monitor 'Site'", "missing required field 'url'"]),
    ("missing name", '[[monitor]]\ntype = "website"\nurl = "https://example.com"\n', ["monitor #1", "missing required field 'name'"]),
    ("interval of zero", block("interval = 0\n"), ["monitor 'Site'", "'interval'", "greater than 0"]),
    ("negative interval", block("interval = -5\n"), ["'interval'", "greater than 0", "-5"]),
    ("timeout of zero", block("timeout = 0\n"), ["'timeout'", "greater than 0"]),
    ("interval written as text", block('interval = "60"\n'), ["'interval'", "must be a number"]),
    ("interval of infinity", block("interval = inf\n"), ["'interval'", "must be a number"]),
    ("negative retries", block("retries = -1\n"), ["'retries'", "whole number"]),
    ("fractional retries", block("retries = 1.5\n"), ["'retries'", "whole number"]),
    ("unknown type", block(base=HEADER.replace("website", "ftp")), ["unknown type", "'ftp'", "website"]),
    ("planned type: proxy", block(base=HEADER.replace("website", "proxy")), ["not supported yet", "'proxy'"]),
    ("planned type: port", block(base=HEADER.replace("website", "port")), ["not supported yet", "'port'"]),
    ("misspelled field", block("intervall = 30\n"), ["unknown field 'intervall'"]),
    ("empty name", block(base=HEADER.replace('"Site"', '""')), ["'name'", "non-empty"]),
    ("empty file", "", ["no monitors found", "[[monitor]]"]),
    ("only comments", "# nothing here\n", ["no monitors found"]),
    ("[monitor] with single brackets", "[monitor]\n" + HEADER, ["double brackets"]),
    ("broken TOML syntax", "[[monitor]\nname = \n", ["not valid TOML"]),
    (
        "several problems reported together",
        '[[monitor]]\nname = "A"\ntype = "ftp"\nurl = "https://example.com"\n\n[[monitor]]\nname = "B"\ntype = "website"\nurl = "https://example.com"\ninterval = 0\n',
        ["monitor 'A'", "unknown type", "monitor 'B'", "'interval'"],
    ),
]


def run_good(name, text, check, workdir):
    path = workdir / "config.toml"
    path.write_text(text)
    try:
        result = check(load_config(path))
    except ConfigError as exc:
        return [f"raised ConfigError: {exc}"], None
    except Exception as exc:  # anything else is a bug in the loader
        return [f"raised {type(exc).__name__}: {exc}"], None
    return ([] if result is True else [result]), None


def run_bad(name, text, needles, workdir):
    path = workdir / "config.toml"
    path.write_text(text)
    try:
        load_config(path)
    except ConfigError as exc:
        message = str(exc)
        problems = [f"message should mention {n!r}" for n in needles if n not in message]
        return problems, message
    except Exception as exc:
        return [f"raised {type(exc).__name__}, not ConfigError: {exc}"], None
    return ["loaded without error, but it should have failed"], None


def report(verdict, name, problems, message=None):
    print(f"{verdict}  {name}")
    if message:
        for line in message.splitlines():
            print(f"      message: {line}")
    for problem in problems:
        print(f"      PROBLEM: {problem}")


def main() -> int:
    failures = 0
    total = 0

    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)

        for name, text, check in GOOD_CASES:
            total += 1
            problems, message = run_good(name, text, check, workdir)
            report("PASS" if not problems else "FAIL", name, problems, message)
            failures += bool(problems)

        for name, text, needles in BAD_CASES:
            total += 1
            problems, message = run_bad(name, text, needles, workdir)
            report("PASS" if not problems else "FAIL", name, problems, message)
            failures += bool(problems)

        # The file problems: missing file, a folder instead of a file.
        for name, path, needles in [
            ("file does not exist", workdir / "nope.toml", ["not found", "config.example.toml"]),
            ("path is a folder", workdir, ["could not read"]),
        ]:
            total += 1
            try:
                load_config(path)
                problems, message = ["loaded without error, but it should have failed"], None
            except ConfigError as exc:
                message = str(exc)
                problems = [f"message should mention {n!r}" for n in needles if n not in message]
            except Exception as exc:
                problems, message = [f"raised {type(exc).__name__}, not ConfigError: {exc}"], None
            report("PASS" if not problems else "FAIL", name, problems, message)
            failures += bool(problems)

        # config.example.toml must load, so the example never goes stale.
        total += 1
        try:
            monitors = load_config(REPO_ROOT / "config.example.toml")
            problems = [] if len(monitors) == 2 else [f"expected 2 monitors, got {len(monitors)}"]
        except Exception as exc:
            problems = [f"config.example.toml failed to load: {exc}"]
        report("PASS" if not problems else "FAIL", "config.example.toml loads", problems)
        failures += bool(problems)

        # The default location, and XDG_CONFIG_HOME overriding it.
        total += 1
        old = os.environ.get("XDG_CONFIG_HOME")
        os.environ["XDG_CONFIG_HOME"] = str(workdir / "xdg")
        try:
            target = default_config_path()
            target.parent.mkdir(parents=True)
            target.write_text(block())
            monitors = load_config()  # no path given: uses the default location
            problems = [] if len(monitors) == 1 else [f"expected 1 monitor, got {len(monitors)}"]
            if not str(target).endswith("service-chaperone/config.toml"):
                problems.append(f"unexpected default path: {target}")
        except Exception as exc:
            problems = [f"default path failed: {type(exc).__name__}: {exc}"]
        finally:
            if old is None:
                os.environ.pop("XDG_CONFIG_HOME", None)
            else:
                os.environ["XDG_CONFIG_HOME"] = old
        report("PASS" if not problems else "FAIL", "default path honours XDG_CONFIG_HOME", problems)
        failures += bool(problems)

    print(f"\n{total - failures} of {total} cases passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())