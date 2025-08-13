from __future__ import annotations

from typing import TYPE_CHECKING

from . import conda_lock_v1, rattler_lock_v6

if TYPE_CHECKING:
    from typing import Final


__all__ = [
    "conda_lock_v1",
    "DUMPERS",
    "rattler_lock_v6",
]

DUMPERS: Final = frozenset(
    {
        conda_lock_v1,
        rattler_lock_v6,
    }
)
