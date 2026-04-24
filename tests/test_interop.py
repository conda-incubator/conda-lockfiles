"""Cross-tool interop tests.

Validate that lockfiles exported by conda-lockfiles can be consumed by the
tools they originated from: pixi for rattler-lock-v6, conda-lock for
conda-lock-v1. Addresses the "and other tools" part of issue #9.

Tests are marked ``interop`` and skipped automatically when the external
tool is not on PATH so local pytest runs stay green without extra setup.
CI installs both tools and runs the full set.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from conda_lockfiles.conda_lock import v1 as conda_lock_v1
from conda_lockfiles.rattler_lock import v6 as rattler_lock_v6

if TYPE_CHECKING:
    from pathlib import Path

    from conda.testing.fixtures import (
        CondaCLIFixture,
        PathFactoryFixture,
        TmpEnvFixture,
    )


pytestmark = pytest.mark.interop


# A single, small, noarch-or-broadly-available package keeps these tests
# fast and avoids flakiness from the solver picking different builds across
# platforms. zlib is what the existing round-trip tests already use.
INTEROP_PACKAGE = "zlib"


def _require(tool: str) -> str:
    """Return the absolute path to ``tool`` or skip the test."""
    path = shutil.which(tool)
    if path is None:
        pytest.skip(f"{tool} not on PATH")
    return path


def test_pixi_consumes_our_rattler_lock_v6(
    path_factory: PathFactoryFixture,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    tmp_path: Path,
) -> None:
    """Our rattler-lock-v6 export must be installable by pixi itself.

    Strategy: create a tiny conda env, export it to pixi.lock, drop a
    matching pixi.toml next to it, then run ``pixi install --frozen`` which
    installs strictly from the lockfile and fails loudly on drift.
    """
    pixi = _require("pixi")

    workspace = tmp_path / "pixi_ws"
    workspace.mkdir()
    lockfile = workspace / rattler_lock_v6.PIXI_LOCK_FILE

    with tmp_env(INTEROP_PACKAGE) as prefix:
        out, err, rc = conda_cli(
            "export",
            f"--prefix={prefix}",
            f"--format={rattler_lock_v6.FORMAT}",
            f"--file={lockfile}",
        )
        assert rc == 0, (out, err)

    # Minimal pixi manifest that matches what we exported. The channel and
    # dependency need to line up with the lockfile for --frozen to accept it.
    (workspace / "pixi.toml").write_text(
        "[workspace]\n"
        'name = "interop"\n'
        'channels = ["conda-forge"]\n'
        'platforms = ["linux-64", "osx-64", "osx-arm64", "win-64"]\n'
        "\n"
        "[dependencies]\n"
        f'{INTEROP_PACKAGE} = "*"\n'
    )

    result = subprocess.run(
        [pixi, "install", "--frozen", "--manifest-path", str(workspace / "pixi.toml")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"pixi install --frozen failed\nstdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    # pixi materialises the env under .pixi/envs/default/conda-meta
    conda_meta = workspace / ".pixi" / "envs" / "default" / "conda-meta"
    assert conda_meta.is_dir(), f"pixi did not create {conda_meta}"
    assert any(
        entry.name.startswith(f"{INTEROP_PACKAGE}-") and entry.suffix == ".json"
        for entry in conda_meta.iterdir()
    ), f"{INTEROP_PACKAGE} not recorded in {conda_meta}"


def test_conda_lock_consumes_our_conda_lock_v1(
    path_factory: PathFactoryFixture,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    tmp_path: Path,
) -> None:
    """Our conda-lock-v1 export must be installable by conda-lock itself.

    conda-lock's unified-format parser requires the ``.conda-lock.yml``
    double extension, so we export there directly and hand it to
    ``conda-lock install --prefix``.
    """
    conda_lock = _require("conda-lock")

    # conda-lock's unified-format parser requires the double extension
    # ``.conda-lock.yml`` so pick that here regardless of what our exporter
    # would name the file by default.
    lockfile = tmp_path / "interop.conda-lock.yml"
    target_prefix = tmp_path / "consumed"

    with tmp_env(INTEROP_PACKAGE) as prefix:
        out, err, rc = conda_cli(
            "export",
            f"--prefix={prefix}",
            f"--format={conda_lock_v1.FORMAT}",
            f"--file={lockfile}",
        )
        assert rc == 0, (out, err)

    result = subprocess.run(
        [conda_lock, "install", "--prefix", str(target_prefix), str(lockfile)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"conda-lock install failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    conda_meta = target_prefix / "conda-meta"
    assert conda_meta.is_dir(), f"conda-lock did not create {conda_meta}"
    assert any(
        entry.name.startswith(f"{INTEROP_PACKAGE}-") and entry.suffix == ".json"
        for entry in conda_meta.iterdir()
    ), f"{INTEROP_PACKAGE} not recorded in {conda_meta}"
