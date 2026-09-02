"""Installed command facade for Ternforge DocOps."""

from __future__ import annotations

import argparse
from pathlib import Path

from ternforge_docops._internal import stale_resources, sync_resources


def _parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(prog="ternforge-docops")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root. Defaults to the current directory.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("sync", help="Materialize canonical DocOps resources.")
    commands.add_parser("check", help="Check canonical DocOps resources.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the DocOps command-line interface and return its exit status."""
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    if args.command == "sync":
        for path in sync_resources(root):
            print(path.relative_to(root))
        return 0

    stale = stale_resources(root)
    if not stale:
        print("DocOps resources are current.")
        return 0
    for path in stale:
        print(f"stale: {path.relative_to(root)}")
    return 1
