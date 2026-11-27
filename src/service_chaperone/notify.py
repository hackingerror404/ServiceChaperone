import logging
import shutil
import subprocess
import apprise

from service_chaperone.models import ServiceState

logger = logging.getLogger(__name__)

APP_NAME = "Service Chaperone"
_TIMEOUT_SECONDS = 5

# Constructs the actual message sent in the notification bus.
def _message(name: str, service_state: ServiceState) -> tuple[str, str] | None:
    if service_state is ServiceState.DOWN:
        return f"{name} is DOWN", f"{APP_NAME} could not reach it."
    if service_state is ServiceState.UP:
        return f"{name} has recovered", f"{APP_NAME} can reach it again."
    return None

# Delivers the notification to your computer.
def _deliver(title: str, body: str, urgent: bool) -> bool:
    program = shutil.which("notify-send")
    if program is None:
        logger.warning(
            "Cannot show a desktop notification: notify-send was not found "
            "(install libnotify)."
        )
        return False

    command = [
        program,
        f"--app-name={APP_NAME}",
        f"--urgency={'critical' if urgent else 'normal'}",
        f"--icon={'dialog-error' if urgent else 'dialog-information'}",
        "--",  # everything after this is text, even if it starts with a hyphen
        title,
        body,
    ]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=_TIMEOUT_SECONDS
        )
    except subprocess.TimeoutExpired:
        logger.warning(
            "Desktop notification timed out after %ss.", _TIMEOUT_SECONDS
        )
        return False
    except OSError as exc:
        logger.warning("Could not run notify-send: %s", exc)
        return False

    if result.returncode != 0:
        detail = result.stderr.strip() or f"exit status {result.returncode}"
        logger.warning("notify-send failed: %s", detail)
        return False
    return True

def notify(name: str, state: ServiceState) -> bool:
    message = _message(name, state)
    if message is None:
        logger.warning("No notification is sent for state %s of %r.", state, name)
        return False
    title, body = message
    return _deliver(title, body, urgent=state is ServiceState.DOWN)

def notify_offline(hosts: str) -> bool:
    title = f"{APP_NAME} is offline"
    body = (
        f"Could not reach {hosts}. "
        "Alerts are paused until the connection returns."
    )
    return _deliver(title, body, urgent=False)

class Notifier:
    """Sends alerts via desktop notification and any configured Apprise URLs."""

    def __init__(
        self,
        urls: tuple[str, ...] = (),
        *,
        apprise_client=None,
        desktop_deliver=_deliver,
    ) -> None:
        self._desktop_deliver = desktop_deliver
        self._apprise = None

        if urls:
            client = apprise_client if apprise_client is not None else apprise.Apprise()
            for index, url in enumerate(urls, start=1):
                if not client.add(url):
                    raise ValueError(
                        f"notify[{index}]: Apprise could not parse this notification URL"
                    )
            self._apprise = client

    def notify(self, name: str, state: ServiceState) -> bool:
        message = _message(name, state)
        if message is None:
            logger.warning("No notification is sent for state %s of %r.", state, name)
            return False

        title, body = message
        desktop_ok = self._desktop_deliver(title, body, urgent=state is ServiceState.DOWN)

        if self._apprise is None:
            return desktop_ok

        notify_type = (
            apprise.NotifyType.FAILURE
            if state is ServiceState.DOWN
            else apprise.NotifyType.SUCCESS
        )
        try:
            remote_ok = bool(
                self._apprise.notify(
                    title=title,
                    body=body,
                    notify_type=notify_type,
                )
            )
        except Exception:
            logger.warning(
                "Failed to deliver alert for %r via configured notify URL(s).",
                name,
            )
            remote_ok = False
        else:
            if not remote_ok:
                logger.warning(
                    "One or more configured notify URL(s) failed to deliver alert for %r.",
                    name,
                )

        return desktop_ok or remote_ok

    def notify_offline(self, hosts: str) -> bool:
        # Machine is offline, so remote URLs aren't reachable; desktop popup only.
        return notify_offline(hosts)