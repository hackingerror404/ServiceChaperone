import logging
import threading

from service_chaperone.connectivity import Connectivity, is_loopback_monitor
from service_chaperone.models import CheckResult, Monitor, ServiceState

logger = logging.getLogger(__name__)

class MonitorStatus:
    def __init__(self):
        self.state = ServiceState.UNKNOWN  # not checked yet
        self.failures = 0  # failed checks in a row

    def record(self, ok: bool, retries: int, online: bool = True) -> ServiceState | None:
        if ok:
            self.failures = 0
            came_back = self.state is ServiceState.DOWN
            self.state = ServiceState.UP  # from UNKNOWN this is silent
            return ServiceState.UP if came_back else None

        if not online and self.failures + 1 >= retries + 1 and self.state is not ServiceState.DOWN:
            # Hold the failure count instead of crossing the DOWN threshold while offline.
            return None

        self.failures += 1
        if self.failures >= retries + 1 and self.state is not ServiceState.DOWN:
            self.state = ServiceState.DOWN
            return ServiceState.DOWN
        return None

class Engine:
    def __init__(
        self,
        monitors,
        on_change,
        connectivity: Connectivity | None = None,
        on_offline=None,
    ):
        self._statuses = {monitor: MonitorStatus() for monitor in monitors}
        self._on_change = on_change
        self._connectivity = connectivity
        self._on_offline = on_offline
        self._offline = False
        self._lock = threading.Lock()

    def handle_result(self, monitor: Monitor, result: CheckResult) -> None:
        use_self_check = (
            self._connectivity is not None and not is_loopback_monitor(monitor)
        )

        # Decide whether we need to probe connectivity, then probe outside the lock.
        need_probe = False
        if use_self_check:
            with self._lock:
                status = self._statuses[monitor]
                would_go_down = (
                    not result.ok
                    and status.state is not ServiceState.DOWN
                    and status.failures + 1 >= monitor.retries + 1
                )
                need_probe = self._offline or would_go_down

        online = self._connectivity.is_online() if need_probe else True

        notify_offline = False
        restored = False
        new_state: ServiceState | None = None
        failures = 0

        with self._lock:
            status = self._statuses[monitor]

            if use_self_check and self._offline:
                if online:
                    self._offline = False
                    restored = True
                    for mon, mon_status in self._statuses.items():
                        if not is_loopback_monitor(mon):
                            mon_status.failures = 0
                    new_state = status.record(result.ok, monitor.retries, online=True)
                    failures = status.failures
                else:
                    # Still offline: hold failure counts and suppress alerts.
                    status.record(result.ok, monitor.retries, online=False)
            elif use_self_check and not online:
                self._offline = True
                notify_offline = True
                status.record(result.ok, monitor.retries, online=False)
            else:
                new_state = status.record(result.ok, monitor.retries, online=True)
                failures = status.failures

        if restored:
            logger.info("Connection restored; resuming normal checks.")

        if notify_offline:
            hosts_text = self._connectivity.hosts_label
            logger.warning(
                "Service Chaperone appears offline (could not reach %s); "
                "pausing DOWN alerts until the connection returns.",
                hosts_text,
            )
            if self._on_offline is not None:
                self._on_offline(hosts_text)
            return

        if new_state is None:
            return

        if new_state is ServiceState.DOWN:
            logger.warning(
                "%s is now DOWN after %d failure(s) in a row (%s)",
                monitor.name,
                failures,
                result.error,
            )
        else:
            logger.info("%s has recovered", monitor.name)
        self._on_change(monitor, new_state)