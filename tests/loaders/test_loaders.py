from __future__ import annotations

from conda_lockfiles.loaders import (
    LOADERS,
    conda_lock_v1,
    rattler_lock_v6,
)


def test_loaders() -> None:
    assert len(LOADERS) == 2
    assert rattler_lock_v6 in LOADERS
    assert conda_lock_v1 in LOADERS
