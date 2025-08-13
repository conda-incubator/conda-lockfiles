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
    for loader in loaders.LOADERS:
        yield CondaEnvironmentSpecifier(
            name=loader.FORMAT,
            environment_spec=loader.environment_spec,
        )


@hookimpl
def conda_environment_exporters() -> Iterable[CondaEnvironmentExporter]:
    for dumper in dumpers.DUMPERS:
        yield CondaEnvironmentExporter(
            name=dumper.FORMAT,
            aliases=dumper.ALIASES,
            default_filenames=dumper.DEFAULT_FILENAMES,
            export=dumper.export,
        )
