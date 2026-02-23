from __future__ import annotations

from contextlib import nullcontext
from typing import TYPE_CHECKING

import pytest
from conda.base.context import context, reset_context

from conda_lockfiles.exceptions import EnvironmentExportNotSupported
from conda_lockfiles.load_yaml import load_yaml
from conda_lockfiles.rattler_lock.v6 import PIXI_LOCK_FILE, RattlerLockV6Loader

from .. import (
    INVALID_LOCKFILES_DIR,
    PIXI_DIR,
    PIXI_METADATA_DIR,
    SINGLE_PACKAGE_ENV,
    SINGLE_PACKAGE_NO_URL_ENV,
    compare_rattler_lock_v6,
)

if TYPE_CHECKING:
    from pathlib import Path

    from conda.testing.fixtures import CondaCLIFixture, TmpEnvFixture
    from pytest_mock import MockerFixture


@pytest.mark.parametrize(
    "prefix,exception",
    [
        pytest.param(SINGLE_PACKAGE_ENV, None, id="single-package"),
        pytest.param(
            SINGLE_PACKAGE_NO_URL_ENV,
            EnvironmentExportNotSupported,
            id="single-package-no-url",
        ),
    ],
)
def test_export_to_rattler_lock_v6(
    mocker: MockerFixture,
    tmp_path: Path,
    conda_cli: CondaCLIFixture,
    prefix: Path,
    exception: Exception | None,
) -> None:
    # mock context.channels to only contain conda-forge
    mocker.patch(
        "conda.base.context.Context.channels",
        new_callable=mocker.PropertyMock,
        return_value=(channels := ("conda-forge",)),
    )
    assert context.channels == channels

    reference = prefix / PIXI_LOCK_FILE
    lockfile = tmp_path / PIXI_LOCK_FILE
    with pytest.raises(exception) if exception else nullcontext():
        out, err, rc = conda_cli("export", f"--prefix={prefix}", f"--file={lockfile}")
        assert not out
        assert not err
        assert rc == 0
        assert compare_rattler_lock_v6(lockfile, reference)

    # TODO: conda's context is not reset when EnvironmentExportNotSupported is raised?
    reset_context()


def test_can_handle(tmp_path: Path) -> None:
    assert RattlerLockV6Loader(PIXI_DIR / PIXI_LOCK_FILE).can_handle()
    assert not RattlerLockV6Loader(PIXI_DIR / "pixi.toml").can_handle()
    assert not RattlerLockV6Loader(tmp_path / PIXI_LOCK_FILE).can_handle()
    assert not RattlerLockV6Loader(tmp_path / "pixi.toml").can_handle()


def test_data() -> None:
    loader = RattlerLockV6Loader(PIXI_DIR / PIXI_LOCK_FILE)
    assert loader._data["version"] == 6
    assert len(loader._data["environments"]["default"]["packages"]["noarch"]) == 2


def test_noarch(
    mocker: MockerFixture,
    conda_cli: CondaCLIFixture,
    tmp_env: TmpEnvFixture,
    tmp_path: Path,
) -> None:
    """Test that noarch packages are listed once within lockfile."""
    platforms = ["linux-64", "osx-arm64"]  # more than one
    lockfile = tmp_path / PIXI_LOCK_FILE
    with tmp_env("--override-channels", "--channel=conda-forge", "boltons") as prefix:
        out, err, rc = conda_cli(
            "export",
            f"--prefix={prefix}",
            f"--file={lockfile}",
            "--override-platforms",
            *(f"--platform={platform}" for platform in platforms),
        )
        assert "Collecting package metadata" in out
        assert not err
        assert rc == 0

        data = load_yaml(lockfile)
        assert (
            sum(
                "conda-forge/noarch/boltons-" in package["conda"]
                for package in data["packages"]
            )
            == 1
        )


@pytest.mark.parametrize(
    "lockfile",
    [
        pytest.param(
            PIXI_METADATA_DIR / PIXI_LOCK_FILE,
            id="valid-lockfile",
        ),
        pytest.param(
            INVALID_LOCKFILES_DIR / "pixi-lock-v6-missing-environments.lock",
            id="missing-environments",
        ),
        pytest.param(
            INVALID_LOCKFILES_DIR / "pixi-lock-v6-missing-packages.lock",
            id="missing-packages",
        ),
        pytest.param(
            INVALID_LOCKFILES_DIR / "pixi-lock-v6-invalid-environments-type.lock",
            id="invalid-environments-type",
        ),
        pytest.param(
            INVALID_LOCKFILES_DIR / "pixi-lock-v6-invalid-platform.lock",
            id="invalid-platform",
        ),
    ],
)
def test_can_handle_validation(lockfile: Path) -> None:
    """Test that can_handle properly validates lockfile structure."""
    loader = RattlerLockV6Loader(lockfile)

    # Valid lockfile should return True, invalid ones should return False
    if lockfile == PIXI_METADATA_DIR / PIXI_LOCK_FILE:
        assert loader.can_handle()
    else:
        assert not loader.can_handle()


def test_can_handle_logs_validation_errors(tmp_path: Path, caplog) -> None:
    """Test that validation errors are logged at DEBUG level."""
    # Create an invalid lockfile
    invalid_lockfile = tmp_path / PIXI_LOCK_FILE
    invalid_lockfile.write_text("version: 6\npackages: []")

    loader = RattlerLockV6Loader(invalid_lockfile)

    # Capture logs at DEBUG level
    with caplog.at_level("DEBUG"):
        result = loader.can_handle()

    # Should return False
    assert not result

    # Should log the validation error (various messages possible)
    assert any(
        "has version 6 but" in record.message.lower() for record in caplog.records
    )
    assert any(str(invalid_lockfile) in record.message for record in caplog.records)
