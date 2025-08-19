from __future__ import annotations

import pytest

from conda_lockfiles.build_number_from_build_string import (
    build_number_from_build_string,
)


@pytest.mark.parametrize(
    "build_string",
    [
        "py310_h0d85af4_0",
        "py36cuda8.0cudnn5.1_0",
        "cuda92py36h1667eeb_0",
        "h244a1a9_0_cpu",
    ],
)
def test_build_number_from_build_string(build_string: str) -> None:
    assert build_number_from_build_string(build_string) == 0
