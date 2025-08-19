from __future__ import annotations

from typing import TYPE_CHECKING

from conda_lockfiles.conda_lock.v1.loader import CONDA_LOCK_FILE, CondaLockV1Loader

from ... import CONDA_LOCK_METADATA_DIR

if TYPE_CHECKING:
    from pathlib import Path


def test_can_handle(tmp_path: Path) -> None:
    assert CondaLockV1Loader(CONDA_LOCK_METADATA_DIR / CONDA_LOCK_FILE).can_handle()
    assert not CondaLockV1Loader(
        CONDA_LOCK_METADATA_DIR / "environment.yaml"
    ).can_handle()
    assert not CondaLockV1Loader(tmp_path / CONDA_LOCK_FILE).can_handle()
    assert not CondaLockV1Loader(tmp_path / "environment.yaml").can_handle()


def test_data() -> None:
    loader = CondaLockV1Loader(CONDA_LOCK_METADATA_DIR / CONDA_LOCK_FILE)
    assert loader._data["version"] == 1
    assert len(loader._data["package"]) == 14
