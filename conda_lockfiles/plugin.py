from __future__ import annotations

from typing import TYPE_CHECKING

from conda.plugins import (
    CondaEnvironmentExporter,
    CondaEnvironmentSpecifier,
    CondaSubcommand,
    hookimpl,
)

from . import cli, dumpers, loaders

if TYPE_CHECKING:
    from collections.abc import Iterable


@hookimpl
def conda_subcommands():
    yield CondaSubcommand(
        name="lockfiles",
        summary="Create new environments from different conda ecosystem lockfiles",
        action=cli.execute,
        configure_parser=cli.configure_parser,
    )


@hookimpl
def conda_environment_specifiers() -> Iterable[CondaEnvironmentSpecifier]:
    for format in loaders.LOCKFILE_FORMATS:
        yield CondaEnvironmentSpecifier(
            name=format.FORMAT,
            environment_spec=format,
        )


@hookimpl
def conda_environment_exporters() -> Iterable[CondaEnvironmentExporter]:
    for format in dumpers.LOCKFILE_FORMATS:
        yield CondaEnvironmentExporter(
            name=format.FORMAT,
            aliases=format.ALIASES,
            default_filenames=format.DEFAULT_FILENAMES,
            export=format.export,
        )
