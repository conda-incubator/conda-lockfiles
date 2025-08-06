from __future__ import annotations

from .base import BaseLoader
from .conda_lock_v1 import CondaLockV1Loader
from .explicit import ExplicitLoader
from .rattler_lock_v6 import RattlerLockV6Loader

__all__ = [
    "BaseLoader",
    "CondaLockV1Loader",
    "ExplicitLoader",
    "LOADERS",
    "RattlerLockV6Loader",
]

LOADERS = (
    CondaLockV1Loader,
    ExplicitLoader,
    RattlerLockV6Loader,
)
