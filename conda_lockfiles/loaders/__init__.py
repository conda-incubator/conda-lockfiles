from __future__ import annotations

from typing import TYPE_CHECKING

from .conda_lock_v1 import CondaLockV1Loader
from .rattler_lock_v6 import RattlerLockV6Loader

if TYPE_CHECKING:
    from typing import Final


__all__ = [
    "CondaLockV1Loader",
    "LOADERS",
    "RattlerLockV6Loader",
]

LOADERS: Final = (
    CondaLockV1Loader,
    RattlerLockV6Loader,
)
