import argparse
from importlib.metadata import version

PROG = "service-chaperone"   # the command people type
DIST = "service-chaperone"   # the name in pyproject.toml

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=PROG)
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {version(DIST)}",
    )
    return parser

def main(argv=None) -> int:
    build_parser().parse_args(argv)
    return 0