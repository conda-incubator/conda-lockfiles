from __future__ import annotations

from conda_lockfiles.loaders import LOADERS, BaseLoader, PixiLoader


def test_loaders() -> None:
    assert LOADERS
    assert BaseLoader not in LOADERS
    assert PixiLoader in LOADERS
