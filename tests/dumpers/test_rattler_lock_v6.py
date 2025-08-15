from __future__ import annotations

from contextlib import nullcontext
from typing import TYPE_CHECKING

import pytest

from conda_lockfiles.dumpers.rattler_lock_v6 import PIXI_LOCK_FILE
from conda_lockfiles.exceptions import EnvironmentExportNotSupported

from .. import SINGLE_PACKAGE_ENV, SINGLE_PACKAGE_NO_URL_ENV

if TYPE_CHECKING:
    from pathlib import Path

    from conda.testing.fixtures import CondaCLIFixture


@pytest.mark.parametrize(
    "prefix,exception",
    [
        pytest.param(SINGLE_PACKAGE_ENV, None, id="single-package"),
        pytest.param(
            SINGLE_PACKAGE_NO_URL_ENV,
            EnvironmentExportNotSupported,
            id="single-package-no-url",
        ),
    ],
)
def test_export_to_rattler_lock_v6(
    tmp_path: Path,
    conda_cli: CondaCLIFixture,
    prefix: Path,
    exception: Exception | None,
) -> None:
    reference = prefix / PIXI_LOCK_FILE
    lockfile = tmp_path / PIXI_LOCK_FILE
    with pytest.raises(exception) if exception else nullcontext():
        out, err, rc = conda_cli("export", f"--prefix={prefix}", f"--file={lockfile}")
        assert not out
        assert not err
        assert rc == 0
        assert lockfile.read_text() == reference.read_text()
