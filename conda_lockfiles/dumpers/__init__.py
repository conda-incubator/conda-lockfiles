from __future__ import annotations

from .conda_lock_v1 import export_to_conda_lock_v1
from .explicit import export_to_explicit
from .rattler_lock import export_to_rattler_lock_v6

__all__ = [
    "export_to_conda_lock_v1",
    "export_to_explicit",
    "export_to_rattler_lock_v6",
    "LOCKFILE_FORMATS",
]

LOCKFILE_FORMATS: dict[str, callable] = {
    "conda-lock-v1": export_to_conda_lock_v1,
    "explicit": export_to_explicit,
    "pixi": export_to_rattler_lock_v6,
    "rattler-lock": export_to_rattler_lock_v6,
}
