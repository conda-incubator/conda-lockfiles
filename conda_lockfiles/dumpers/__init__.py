from __future__ import annotations

from typing import TYPE_CHECKING

from .conda_lock_v1 import export_to_conda_lock_v1
from .explicit import export_to_explicit
from .rattler_lock_v6 import export_to_rattler_lock_v6

if TYPE_CHECKING:
    from typing import Callable


__all__ = [
    "export_to_conda_lock_v1",
    "export_to_explicit",
    "export_to_rattler_lock_v6",
    "LOCKFILE_FORMATS",
]

LOCKFILE_FORMATS: dict[str, Callable] = {
    "conda-lock-v1": export_to_conda_lock_v1,
    "explicit": export_to_explicit,
    "rattler-lock-v6": export_to_rattler_lock_v6,
}
