import argparse
import logging
import sys
from importlib.metadata import version
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler

from service_chaperone.config import ConfigError, load_config
from service_chaperone.connectivity import Connectivity
from service_chaperone.engine import Engine
from service_chaperone.notify import Notifier
from service_chaperone.scheduler import add_monitor_jobs

PROG = "service-chaperone"   # the command people type
DIST = "service-chaperone"   # the name in pyproject.toml

logger = logging.getLogger(__name__)

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=PROG)
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {version(DIST)}",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="check every monitor on its schedule until stopped")
    run.add_argument(
        "--config",
        type=Path,
        help="path to the config file (default: ~/.config/service-chaperone/config.toml)",
    )
    return parser

def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    for noisy in ("httpx", "httpcore", "apscheduler"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    logging.getLogger("apprise").setLevel(logging.CRITICAL) 

def run_command(args) -> int:
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return 1

    setup_logging()
    scheduler = BlockingScheduler()
    connectivity = Connectivity()
    notifier = Notifier(urls=config.notify)
    engine = Engine(
        config.monitors,
        on_change=lambda monitor, state: notifier.notify(monitor.name, state),
        connectivity=connectivity,
        on_offline=notifier.notify_offline,
    )
    add_monitor_jobs(scheduler, config.monitors, on_result=engine.handle_result)
    logger.info("Watching %d monitor(s) with %d alert destination(s). Press Ctrl-C to stop.", len(config.monitors), len(config.notify))
    try:
        scheduler.start()  # holds the terminal until interrupted
    except (KeyboardInterrupt, SystemExit):
        logger.info("Stopping; waiting for any check in progress to finish.")
        if scheduler.running:
            scheduler.shutdown(wait=False)
    return 0

def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run":
        return run_command(args)
    return 0