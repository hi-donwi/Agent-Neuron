"""Command-line entry point: `python -m neuron_lab`."""

import argparse
import json
import platform
import sys
from collections.abc import Sequence

from neuron_lab import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="neuron-lab",
        description="Agent-Neuron lab. Commands arrive with the milestones in ROADMAP.md.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    version = commands.add_parser("version", help="print lab build information")
    version.add_argument("--json", action="store_true", help="print build information as JSON")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    info = {"version": __version__, "python": platform.python_version()}
    if args.json:
        print(json.dumps(info))
    else:
        print(f"neuron-lab {info['version']} (python {info['python']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
