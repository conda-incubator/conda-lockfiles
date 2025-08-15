from __future__ import annotations

import re
from contextlib import nullcontext
from typing import TYPE_CHECKING

import pytest

from conda_lockfiles.dumpers.conda_lock_v1 import CONDA_LOCK_FILE
from conda_lockfiles.exceptions import EnvironmentExportNotSupported

from .. import SINGLE_PACKAGE_ENV, SINGLE_PACKAGE_NO_URL_ENV

if TYPE_CHECKING:
    from pathlib import Path

    from conda.testing.fixtures import CondaCLIFixture


RE_CREATED_AT = re.compile(r"created_at: .+Z")


def _normalize_lockfile(lockfile: Path) -> str:
    return RE_CREATED_AT.sub("created_at: 'TIMESTAMP'", lockfile.read_text())


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
def test_export_to_conda_lock_v1(
    tmp_path: Path,
    conda_cli: CondaCLIFixture,
    prefix: Path,
    exception: Exception | None,
) -> None:
    reference = prefix / CONDA_LOCK_FILE
    lockfile = tmp_path / CONDA_LOCK_FILE
    with pytest.raises(exception) if exception else nullcontext():
        out, err, rc = conda_cli("export", f"--prefix={prefix}", f"--file={lockfile}")
        assert not out
        assert not err
        assert rc == 0
        assert _normalize_lockfile(lockfile) == _normalize_lockfile(reference)
