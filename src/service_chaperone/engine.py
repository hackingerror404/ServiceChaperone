import logging
import threading

from service_chaperone.models import CheckResult, Monitor, ServiceState

logger = logging.getLogger(__name__)

class MonitorStatus:
    def __init__(self):
        self.state = ServiceState.UNKNOWN  # not checked yet
        self.failures = 0  # failed checks in a row

    def record(self, ok: bool, retries: int) -> ServiceState | None:
        if ok:
            self.failures = 0
            came_back = self.state is ServiceState.DOWN
            self.state = ServiceState.UP  # from UNKNOWN this is silent
            return ServiceState.UP if came_back else None

        self.failures += 1
        if self.failures >= retries + 1 and self.state is not ServiceState.DOWN:
            self.state = ServiceState.DOWN
            return ServiceState.DOWN
        return None


class Engine:
    def __init__(self, monitors, on_change):
        self._statuses = {monitor: MonitorStatus() for monitor in monitors}
        self._on_change = on_change
        self._lock = threading.Lock()

    def handle_result(self, monitor: Monitor, result: CheckResult) -> None:
        with self._lock:
            status = self._statuses[monitor]
            new_state = status.record(result.ok, monitor.retries)
            failures = status.failures
        if new_state is None:
            return

        if new_state is ServiceState.DOWN:
            logger.warning(
                "%s is now DOWN after %d failure(s) in a row (%s)",
                monitor.name, failures, result.error,
            )
        else:
            logger.info("%s has recovered", monitor.name)
        self._on_change(monitor, new_state)