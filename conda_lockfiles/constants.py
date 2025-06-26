from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Final


CONDA_LOCK_FILE: Final = "conda-lock.yml"
EXPLICIT_KEY: Final = "@EXPLICIT"
PIXI_LOCK_FILE: Final = "pixi.lock"

HASH_KEYS: Final = {"md5", "sha256"}
OVERRIDE_KEYS: Final = {"depends", "constrains"}
