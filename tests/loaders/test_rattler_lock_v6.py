from __future__ import annotations

from typing import TYPE_CHECKING

from conda_lockfiles.constants import PIXI_LOCK_FILE
from conda_lockfiles.loaders.rattler_lock_v6 import RattlerLockV6Loader

from .. import PIXI_DIR

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MockerFixture


def test_rattler_lock_v6_loader_supports(mocker: MockerFixture, tmp_path: Path) -> None:
    assert RattlerLockV6Loader.supports(PIXI_DIR / PIXI_LOCK_FILE)
    assert not RattlerLockV6Loader.supports(PIXI_DIR / "pixi.toml")
    assert not RattlerLockV6Loader.supports(tmp_path / PIXI_LOCK_FILE)
    assert not RattlerLockV6Loader.supports(tmp_path / "pixi.toml")


def test_rattler_lock_v6_loader_load() -> None:
    loader = RattlerLockV6Loader(PIXI_DIR / PIXI_LOCK_FILE)
    assert loader.data["version"] == 6
    assert len(loader.data["environments"]["default"]["packages"]["noarch"]) == 2
