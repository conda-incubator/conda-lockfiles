from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from conda.base.context import context

from conda_lockfiles.conda_lock import v1 as conda_lock_v1
from conda_lockfiles.load_yaml import load_yaml
from conda_lockfiles.rattler_lock import v6 as rattler_lock_v6

from . import compare_conda_lock_v1, compare_rattler_lock_v6

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Callable

    from conda.testing.fixtures import (
        CondaCLIFixture,
        PathFactoryFixture,
        TmpEnvFixture,
    )


@pytest.mark.parametrize(
    "format,filename,compare",
    [
        (
            rattler_lock_v6.FORMAT,
            rattler_lock_v6.PIXI_LOCK_FILE,
            compare_rattler_lock_v6,
        ),
        (
            conda_lock_v1.FORMAT,
            conda_lock_v1.CONDA_LOCK_FILE,
            compare_conda_lock_v1,
        ),
    ],
)
def test_export(
    path_factory: PathFactoryFixture,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    format: str,
    filename: str,
    compare: Callable[[Path, Path], bool],
) -> None:
    lockfile = path_factory(filename)
    prefix2 = path_factory()
    lockfile2 = path_factory(filename)

    with tmp_env("zlib") as prefix:
        # export environment to a lockfile
        out, err, rc = conda_cli(
            "export",
            f"--prefix={prefix}",
            f"--format={format}",
            f"--file={lockfile}",
        )
        assert not out
        assert not err
        assert rc == 0

        # create a new environment from the lockfile
        out, err, rc = conda_cli(
            "env",
            "create",
            f"--prefix={prefix2}",
            f"--env-spec={format}",
            f"--file={lockfile}",
        )
        assert out
        assert not err
        assert rc == 0

        # export new environment to a lockfile, should be identical
        out, err, rc = conda_cli(
            "export",
            f"--prefix={prefix2}",
            f"--format={format}",
            f"--file={lockfile2}",
        )
        assert not out
        assert not err
        assert rc == 0
        assert compare(lockfile, lockfile2)


@pytest.mark.parametrize(
    "format,filename,get_platforms",
    [
        (
            conda_lock_v1.FORMAT,
            conda_lock_v1.CONDA_LOCK_FILE,
            lambda lockfile: tuple(load_yaml(lockfile)["metadata"]["platforms"]),
        ),
        (
            rattler_lock_v6.FORMAT,
            rattler_lock_v6.PIXI_LOCK_FILE,
            lambda lockfile: tuple(
                load_yaml(lockfile)["environments"]["default"]["packages"]
            ),
        ),
    ],
)
def test_multiplatform_export(
    path_factory: PathFactoryFixture,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    format: str,
    filename: str,
    get_platforms: Callable[[Path], tuple[str, ...]],
):
    platforms = tuple(sorted({context.subdir, "linux-64", "osx-arm64", "win-64"}))
    lockfile = path_factory(filename)
    with tmp_env("zlib") as prefix:
        # export environment to a lockfile
        out, err, rc = conda_cli(
            "export",
            f"--prefix={prefix}",
            f"--format={format}",
            f"--file={lockfile}",
            "--override-platforms",
            *(f"--platform={platform}" for platform in platforms),
        )
        assert "Collecting package metadata" in out, out
        assert not err
        assert rc == 0
        assert get_platforms(lockfile) == platforms

        for platform in platforms:
            # create a new environment from the lockfile
            out, err, rc = conda_cli(
                "env",
                "create",
                f"--prefix={path_factory()}",
                f"--env-spec={format}",
                f"--file={lockfile}",
                f"--platform={platform}",
            )
            assert out
            assert not err
            assert rc == 0
