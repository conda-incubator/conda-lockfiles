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
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from conda_lockfiles.conda_lock import v1 as conda_lock_v1
from conda_lockfiles.rattler_lock import v6 as rattler_lock_v6

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Callable

    from conda.testing.fixtures import (
        CondaCLIFixture,
        TmpEnvFixture,
    )


pytestmark = pytest.mark.interop


# A single, small, broadly-available package keeps these tests fast and
# avoids flakiness from the solver picking different builds across
# platforms. zlib is what the existing round-trip tests already use.
INTEROP_PACKAGE = "zlib"


@pytest.fixture
def external_tool(request: pytest.FixtureRequest) -> str:
    """Resolve an external tool binary on PATH or skip.

    Parametrized tests request it indirectly via ``indirect=["external_tool"]``
    passing the tool name as the fixture value; the fixture returns the
    absolute path to the binary or skips the test when the tool is missing.
    """
    tool = request.param
    path = shutil.which(tool)
    if path is None:
        pytest.skip(f"{tool} not on PATH")
    return path


def run_subprocess(argv: list[str], *, what: str) -> None:
    """Run ``argv``, failing the test with stdout/stderr on a non-zero exit."""
    result = subprocess.run(argv, capture_output=True, text=True)
    assert result.returncode == 0, (
        f"{what} failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def consume_with_pixi(tool: str, lockfile: Path, workdir: Path) -> Path:
    """Install the lockfile with pixi, return the prefix pixi created.

    pixi has no "install this lockfile at this prefix" mode, so we drop a
    minimal pixi.toml that matches the exported lockfile next to it and run
    ``pixi install --frozen`` which refuses to proceed on drift.
    """
    (workdir / "pixi.toml").write_text(
        "[workspace]\n"
        'name = "interop"\n'
        'channels = ["conda-forge"]\n'
        'platforms = ["linux-64", "osx-64", "osx-arm64", "win-64"]\n'
        "\n"
        "[dependencies]\n"
        f'{INTEROP_PACKAGE} = "*"\n'
    )
    run_subprocess(
        [tool, "install", "--frozen", "--manifest-path", str(workdir / "pixi.toml")],
        what="pixi install --frozen",
    )
    return workdir / ".pixi" / "envs" / "default"


def consume_with_conda_lock(tool: str, lockfile: Path, workdir: Path) -> Path:
    """Install the lockfile with conda-lock, return the target prefix."""
    prefix = workdir / "consumed"
    run_subprocess(
        [tool, "install", "--prefix", str(prefix), str(lockfile)],
        what="conda-lock install",
    )
    return prefix


@dataclass(frozen=True)
class InteropCase:
    """One export-then-consume scenario for a single lockfile format."""

    id: str
    format: str
    # Filename to write the export to. Some consumers care about the
    # extension: conda-lock's unified-format parser requires
    # ``.conda-lock.yml``, pixi wants the file literally named ``pixi.lock``.
    filename: str
    tool: str
    consume: Callable[[str, "Path", "Path"], "Path"]


CASES = [
    InteropCase(
        id="pixi-consumes-rattler-lock-v6",
        format=rattler_lock_v6.FORMAT,
        filename=rattler_lock_v6.PIXI_LOCK_FILE,
        tool="pixi",
        consume=consume_with_pixi,
    ),
    InteropCase(
        id="conda-lock-consumes-conda-lock-v1",
        format=conda_lock_v1.FORMAT,
        filename="interop.conda-lock.yml",
        tool="conda-lock",
        consume=consume_with_conda_lock,
    ),
]


@pytest.mark.parametrize(
    "case,external_tool",
    [pytest.param(case, case.tool, id=case.id) for case in CASES],
    indirect=["external_tool"],
)
def test_external_tool_consumes_our_export(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    tmp_path: Path,
    case: InteropCase,
    external_tool: str,
) -> None:
    """Our export must be installable by the tool that owns the format."""
    workdir = tmp_path / case.id
    workdir.mkdir()
    lockfile = workdir / case.filename

    with tmp_env(INTEROP_PACKAGE) as prefix:
        out, err, rc = conda_cli(
            "export",
            f"--prefix={prefix}",
            f"--format={case.format}",
            f"--file={lockfile}",
        )
        assert rc == 0, (out, err)

    consumed_prefix = case.consume(external_tool, lockfile, workdir)

    conda_meta = consumed_prefix / "conda-meta"
    assert conda_meta.is_dir(), f"{case.tool} did not create {conda_meta}"
    assert any(
        entry.name.startswith(f"{INTEROP_PACKAGE}-") and entry.suffix == ".json"
        for entry in conda_meta.iterdir()
    ), f"{INTEROP_PACKAGE} not recorded in {conda_meta}"
