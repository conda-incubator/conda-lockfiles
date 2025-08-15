from __future__ import annotations

from typing import TYPE_CHECKING

from conda.plugins import hookimpl
from conda.plugins.types import CondaEnvironmentExporter, CondaEnvironmentSpecifier

if TYPE_CHECKING:
    from collections.abc import Iterable


@hookimpl
def conda_environment_specifiers() -> Iterable[CondaEnvironmentSpecifier]:
    from .loaders import conda_lock_v1, rattler_lock_v6

    yield CondaEnvironmentSpecifier(
        name=conda_lock_v1.FORMAT,
        environment_spec=conda_lock_v1.CondaLockV1Loader,
    )
    yield CondaEnvironmentSpecifier(
        name=rattler_lock_v6.FORMAT,
        environment_spec=rattler_lock_v6.RattlerLockV6Loader,
    )


@hookimpl
def conda_environment_exporters() -> Iterable[CondaEnvironmentExporter]:
    from .dumpers import conda_lock_v1, rattler_lock_v6

    yield CondaEnvironmentExporter(
        name=conda_lock_v1.FORMAT,
        aliases=conda_lock_v1.ALIASES,
        default_filenames=conda_lock_v1.DEFAULT_FILENAMES,
        export=conda_lock_v1.export,
    )
    yield CondaEnvironmentExporter(
        name=rattler_lock_v6.FORMAT,
        aliases=rattler_lock_v6.ALIASES,
        default_filenames=rattler_lock_v6.DEFAULT_FILENAMES,
        export=rattler_lock_v6.export,
    )
