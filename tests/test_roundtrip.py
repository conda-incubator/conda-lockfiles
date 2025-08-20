from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda_lockfiles.conda_lock.v1 import dumper as conda_lock_v1
from conda_lockfiles.rattler_lock.v6 import dumper as rattler_lock_v6

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
        conda_cli(
            "env",
            "create",
            f"--prefix={prefix2}",
            f"--env-spec={format}",
            f"--file={lockfile}",
        )

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
