"""
conda lockfiles create subcommand for CLI
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse

HELP = "Create a conda environment from a lock file."


def configure_parser(parser: argparse.ArgumentParser) -> None:
    from conda.base.context import context
    from conda.cli.helpers import add_parser_prefix

    parser.description = HELP

    add_parser_prefix(parser, True)
    parser.add_argument("path", help="Path to lockfile")
    parser.add_argument(
        "-e",
        "--environment",
        default="default",
        help="Environment name in lockfile",
    )
    parser.add_argument(
        "-s",
        "--subdir",
        "--platform",
        dest="platform",
        default=context.subdir,
        help="Target platform",
    )
    parser.set_defaults(func=execute)


def execute(args: argparse.Namespace) -> int:
    from conda.base.context import context

    from ..create import create_environment_from_lockfile

    create_environment_from_lockfile(
        lockfile=args.path,
        prefix=context.target_prefix,
        environment=args.environment,
        platform=args.platform,
        dry_run=context.dry_run,
        download_only=context.download_only,
        verbose=not context.json and context.verbose,
    )
    return 0
