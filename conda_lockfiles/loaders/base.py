from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING

from conda.common.serialize import yaml_safe_load

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any


@cache
def load_yaml(path: Path) -> dict[str, Any]:
    with path.open() as fh:
        return yaml_safe_load(fh)


def build_number_from_build_string(build_string: str) -> int:
    "Assume build number is underscore-separated, all-digit substring in build_string"
    return int(
        next(
            (
                part
                for part in build_string.split("_")
                if all(digit.isdigit() for digit in part)
            ),
            0,
        )
    )
