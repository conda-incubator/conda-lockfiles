from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from conda_lockfiles.dumpers import conda_lock_v1, rattler_lock_v6

from . import normalize_conda_lock_v1

if TYPE_CHECKING:
    from typing import Callable

    from conda.testing.fixtures import (
        CondaCLIFixture,
        PathFactoryFixture,
        TmpEnvFixture,
    )
    from pytest import MonkeyPatch


@pytest.mark.parametrize(
    "format,filename,read_lockfile",
    [
        (rattler_lock_v6.FORMAT, rattler_lock_v6.PIXI_LOCK_FILE, Path.read_text),
        (
            conda_lock_v1.FORMAT,
            conda_lock_v1.CONDA_LOCK_FILE,
            normalize_conda_lock_v1,
        ),
    ],
)
def test_export(
    path_factory: PathFactoryFixture,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    monkeypatch: MonkeyPatch,
    format: str,
    filename: str,
    read_lockfile: Callable[[Path], str],
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
        monkeypatch.setenv("CONDA_ENV_SPEC", format)
        conda_cli(
            "env",
            "create",
            f"--prefix={prefix2}",
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
        assert read_lockfile(lockfile) == read_lockfile(lockfile)
