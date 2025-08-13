from __future__ import annotations

from conda_lockfiles.dumpers import DUMPERS, conda_lock_v1, rattler_lock_v6


def test_dumpers() -> None:
    assert len(DUMPERS) == 2
    assert conda_lock_v1 in DUMPERS
    assert rattler_lock_v6 in DUMPERS
