from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from conda.common.compat import on_win

from conda_lockfiles.constants import CONDA_LOCK_FILE, PIXI_LOCK_FILE
from conda_lockfiles.create import create_environment_from_lockfile

from . import (
    CONDA_LOCK_METADATA_DIR,
    PIXI_METADATA_DIR,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_create_environment_from_lockfile_pixi_metadata(tmp_path: Path) -> None:
    create_environment_from_lockfile(
        PIXI_METADATA_DIR / PIXI_LOCK_FILE,
        tmp_path,
        environment="default",
        platform="linux-64",
    )
    env_record_path = tmp_path / "conda-meta" / "tzdata-2025b-h78e105d_0.json"
    assert env_record_path.is_file()
    data = json.loads(env_record_path.read_bytes())
    assert data["license"] == "ONLY_IN_LOCKFILE"


@pytest.mark.skipif(
    condition=on_win,
    reason="linux environment creation is not supported on Windows",
)
def test_create_environment_from_lockfile_conda_lock_metadata(tmp_path: Path) -> None:
    create_environment_from_lockfile(
        CONDA_LOCK_METADATA_DIR / CONDA_LOCK_FILE,
        tmp_path,
        platform="linux-64",
    )
    env_record_path = tmp_path / "conda-meta" / "libsqlite-3.50.0-hee588c1_0.json"
    assert env_record_path.is_file()
    data = json.loads(env_record_path.read_bytes())
    # package/repodata has .<2.0a0
    assert "libzlib >=1.3.1,<2.0a1" in data["depends"]
