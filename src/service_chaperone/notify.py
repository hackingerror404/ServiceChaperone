import logging
import shutil
import subprocess

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
    # Urgent state here makes the notification not disappear until clicked. Might change later if too annoying.