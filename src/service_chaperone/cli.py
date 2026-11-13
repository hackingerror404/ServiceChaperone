import argparse
import logging
import sys
from importlib.metadata import version
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler

from service_chaperone.config import ConfigError, load_config
from service_chaperone.scheduler import add_monitor_jobs

PROG = "service-chaperone"   # the command people type
DIST = "service-chaperone"   # the name in pyproject.toml

logger = logging.getLogger(__name__)

def main(argv=None) -> int:
    build_parser().parse_args(argv)
    return 0

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

def run_command(args) -> int:
    try:
        monitors = load_config(args.config)
    except ConfigError as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return 1

    setup_logging()
    scheduler = BlockingScheduler()
    add_monitor_jobs(scheduler, monitors)
    logger.info("Watching %d monitor(s). Press Ctrl-C to stop.", len(monitors))
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