from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda_lockfiles.dumpers import conda_lock_v1, rattler_lock_v6

if TYPE_CHECKING:
    from conda.testing.fixtures import (
        CondaCLIFixture,
        PathFactoryFixture,
        TmpEnvFixture,
    )


@pytest.mark.parametrize(
    "format,filename",
    [
        (rattler_lock_v6.FORMAT, rattler_lock_v6.PIXI_LOCK_FILE),
        (conda_lock_v1.FORMAT, conda_lock_v1.CONDA_LOCK_FILE),
    ],
)
def test_export(
    path_factory: PathFactoryFixture,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    format: str,
    filename: str,
) -> None:
    lockfile = path_factory(filename)
    prefix2 = path_factory()
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
        conda_cli("env", "create", f"--file={lockfile}", f"--prefix={prefix2}")

        # export new environment to a lockfile, should be identical
        out, err, rc = conda_cli("export", f"--prefix={prefix2}", f"--format={format}")
        assert lockfile.read_text() == out
        assert not err
        assert rc == 0
