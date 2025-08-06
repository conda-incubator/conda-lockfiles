from __future__ import annotations

from conda_lockfiles.loaders import (
    LOADERS,
    BaseLoader,
    CondaLockV1Loader,
    RattlerLockV6Loader,
)


def test_loaders() -> None:
    assert LOADERS
    assert BaseLoader not in LOADERS
    assert RattlerLockV6Loader in LOADERS
    assert CondaLockV1Loader in LOADERS
