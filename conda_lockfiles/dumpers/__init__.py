from __future__ import annotations

from typing import TYPE_CHECKING

from . import conda_lock_v1, rattler_lock_v6

if TYPE_CHECKING:
    from types import ModuleType


__all__ = [
    "conda_lock_v1",
    "rattler_lock",
    "LOCKFILE_FORMATS",
]

LOCKFILE_FORMATS: tuple[ModuleType, ...] = (
    conda_lock_v1,
    rattler_lock_v6,
)
