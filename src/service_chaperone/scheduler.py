import logging
from datetime import datetime

from apscheduler.triggers.interval import IntervalTrigger

from service_chaperone.checks.website import check_website

logger = logging.getLogger(__name__)

CHECKERS = {"website": check_website}

def _format_result(monitor, result) -> str:
    if result.ok:
        timing = f"{result.response_ms:.1f} ms" if result.response_ms is not None else "no timing"
        return f"{monitor.name}: UP ({timing})"
    return f"{monitor.name}: DOWN ({result.error})"

def _run_check(monitor, on_result):
    try:
        result = CHECKERS[monitor.type](monitor.url, monitor.timeout)
        if result.ok:
            logger.info(_format_result(monitor, result))
        else:
            logger.warning(_format_result(monitor, result))
        if on_result is not None:
            on_result(monitor, result)
    except Exception:
        logger.exception(
            "Check of %s crashed; it will run again at its next interval.",
            monitor.name,
        )

def add_monitor_jobs(scheduler, monitors, on_result=None) -> None:
    for index, monitor in enumerate(monitors, start=1):
        scheduler.add_job(
            _run_check,
            trigger=IntervalTrigger(seconds=monitor.interval),
            args=(monitor, on_result),
            id=f"monitor-{index}",
            name=monitor.name,
            next_run_time=datetime.now(scheduler.timezone),  # check right away
            max_instances=1, 
            coalesce=True,  # after a sleep, merge missed runs into one
            misfire_grace_time=max(1, int(monitor.interval)),  # late beats skipped
        )