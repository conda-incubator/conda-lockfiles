from __future__ import annotations

from typing import TYPE_CHECKING

from conda_lockfiles.loaders.rattler_lock_v6 import PIXI_LOCK_FILE, RattlerLockV6Loader

from .. import PIXI_DIR

if TYPE_CHECKING:
    from pathlib import Path


def test_can_handle(tmp_path: Path) -> None:
    assert RattlerLockV6Loader(PIXI_DIR / PIXI_LOCK_FILE).can_handle()
    assert not RattlerLockV6Loader(PIXI_DIR / "pixi.toml").can_handle()
    assert not RattlerLockV6Loader(tmp_path / PIXI_LOCK_FILE).can_handle()
    assert not RattlerLockV6Loader(tmp_path / "pixi.toml").can_handle()


def test_data() -> None:
    loader = RattlerLockV6Loader(PIXI_DIR / PIXI_LOCK_FILE)
    assert loader._data["version"] == 6
    assert len(loader._data["environments"]["default"]["packages"]["noarch"]) == 2
