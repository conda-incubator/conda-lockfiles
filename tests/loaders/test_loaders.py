from __future__ import annotations

from conda_lockfiles.loaders import (
    LOADERS,
    CondaLockV1Loader,
    RattlerLockV6Loader,
)


def test_loaders() -> None:
    assert LOADERS
    assert RattlerLockV6Loader in LOADERS
    assert CondaLockV1Loader in LOADERS
