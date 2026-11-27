"""Verify Apprise notification plumbing, startup validation, and secret redaction."""

import logging
from pathlib import Path
import sys
import tempfile

from service_chaperone.config import ConfigError, load_config
from service_chaperone.models import ServiceState
from service_chaperone.notify import Notifier


class _FakeApprise:
    def __init__(self, *, notify_result: bool = True, reject_urls: set[str] | None = None):
        self.added: list[str] = []
        self.sent: list[dict] = []
        self.notify_result = notify_result
        self.reject_urls = reject_urls or set()

    def add(self, url: str) -> bool:
        if url in self.reject_urls:
            return False
        self.added.append(url)
        return True

    def notify(self, *, title: str, body: str, notify_type=None) -> bool:
        self.sent.append({"title": title, "body": body, "notify_type": notify_type})
        return self.notify_result


class _LogCollector(logging.Handler):
    def __init__(self):
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record):
        self.messages.append(self.format(record))


def main() -> int:
    failures: list[str] = []

    def check(label: str, condition: bool, detail: str = "") -> None:
        if condition:
            print(f"[PASS] {label}")
        else:
            msg = f"[FAIL] {label}" + (f" -> {detail}" if detail else "")
            print(msg)
            failures.append(msg)

    notify_logger = logging.getLogger("service_chaperone.notify")
    collector = _LogCollector()
    notify_logger.addHandler(collector)
    notify_logger.setLevel(logging.DEBUG)

    try:
        # 1. With a notify list: sends DOWN and UP alerts to every URL via Apprise + desktop
        fake_apprise = _FakeApprise()
        desktop_calls: list[tuple[str, str, bool]] = []

        def fake_desktop(title: str, body: str, urgent: bool) -> bool:
            desktop_calls.append((title, body, urgent))
            return True

        urls = (
            "mailto://alice:s3cr3tpass@example.com",
            "discord://123456/tok_supersecret999",
        )
        notifier = Notifier(
            urls=urls,
            apprise_client=fake_apprise,
            desktop_deliver=fake_desktop,
        )
        ok_down = notifier.notify("My site", ServiceState.DOWN)
        ok_up = notifier.notify("My site", ServiceState.UP)

        check(
            "With notify list: adds every URL and sends both DOWN and UP alerts",
            ok_down
            and ok_up
            and fake_apprise.added == list(urls)
            and len(fake_apprise.sent) == 2
            and "DOWN" in fake_apprise.sent[0]["title"]
            and "recovered" in fake_apprise.sent[1]["title"]
            and len(desktop_calls) == 2,
            f"added={fake_apprise.added!r}, sent={fake_apprise.sent!r}, desktop={desktop_calls!r}",
        )

        # 2. With no notify list: desktop notification only
        desktop_calls.clear()
        unused_apprise = _FakeApprise()
        notifier_desktop_only = Notifier(
            urls=(),
            apprise_client=unused_apprise,
            desktop_deliver=fake_desktop,
        )
        notifier_desktop_only.notify("My site", ServiceState.DOWN)
        check(
            "With no notify list: sends desktop notification only, never calls Apprise",
            len(desktop_calls) == 1
            and len(unused_apprise.added) == 0
            and len(unused_apprise.sent) == 0,
            f"desktop={desktop_calls!r}, apprise_sent={unused_apprise.sent!r}",
        )

        # 3 & 4. Startup validation rejects bad Apprise URLs and never leaks secrets
        secret_pass = "s3cr3tpass"
        secret_token = "tok_supersecret999"

        with tempfile.TemporaryDirectory() as tmp:
            bad_cfg = Path(tmp) / "bad.toml"
            bad_cfg.write_text(
                f'notify = ["bogusscheme://alice:{secret_pass}@example.com/{secret_token}"]\n\n'
                '[[monitor]]\nname = "Site"\ntype = "website"\nurl = "https://example.com"\n'
            )
            try:
                load_config(bad_cfg)
                check("Invalid Apprise URL fails at startup", False, "loaded without error")
            except ConfigError as exc:
                msg = str(exc)
                check(
                    "Invalid Apprise URL fails at startup with clear message and no secret leak",
                    "Apprise could not parse" in msg
                    and secret_pass not in msg
                    and secret_token not in msg,
                    msg,
                )

            good_cfg = Path(tmp) / "good.toml"
            good_cfg.write_text(
                f'notify = ["mailto://alice:{secret_pass}@example.com"]\n\n'
                '[[monitor]]\nname = "Site"\ntype = "website"\nurl = "https://example.com"\n'
            )
            loaded = load_config(good_cfg)
            check(
                "Valid Apprise URL loads and repr(Config) never leaks password",
                len(loaded.notify) == 1 and secret_pass not in repr(loaded),
                repr(loaded),
            )

        # 4b. Failed delivery log never leaks passwords or tokens
        collector.messages.clear()
        failing_apprise = _FakeApprise(notify_result=False)
        failing_notifier = Notifier(
            urls=urls,
            apprise_client=failing_apprise,
            desktop_deliver=fake_desktop,
        )
        failing_notifier.notify("My site", ServiceState.DOWN)
        joined_logs = "\n".join(collector.messages)
        check(
            "Failed delivery warning logs never contain passwords or tokens",
            len(collector.messages) >= 1
            and secret_pass not in joined_logs
            and secret_token not in joined_logs,
            joined_logs,
        )
    finally:
        notify_logger.removeHandler(collector)

    print(f"\nFinished with {len(failures)} failure(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())