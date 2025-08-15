from __future__ import annotations

from contextlib import nullcontext
from typing import TYPE_CHECKING

import pytest
from conda.base.context import context, reset_context

from conda_lockfiles.dumpers.conda_lock_v1 import CONDA_LOCK_FILE
from conda_lockfiles.exceptions import EnvironmentExportNotSupported

from .. import (
    SINGLE_PACKAGE_ENV,
    SINGLE_PACKAGE_NO_URL_ENV,
    normalize_conda_lock_v1,
)

if TYPE_CHECKING:
    from pathlib import Path

    from conda.testing.fixtures import CondaCLIFixture
    from pytest_mock import MockerFixture


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
    mocker: MockerFixture,
    tmp_path: Path,
    conda_cli: CondaCLIFixture,
    prefix: Path,
    exception: Exception | None,
) -> None:
    # mock context.channels to only contain conda-forge
    mocker.patch(
        "conda.base.context.Context.channels",
        new_callable=mocker.PropertyMock,
        return_value=(channels := ("conda-forge",)),
    )
    assert context.channels == channels

    reference = prefix / CONDA_LOCK_FILE
    lockfile = tmp_path / CONDA_LOCK_FILE
    with pytest.raises(exception) if exception else nullcontext():
        out, err, rc = conda_cli("export", f"--prefix={prefix}", f"--file={lockfile}")
        assert not out
        assert not err
        assert rc == 0
        assert normalize_conda_lock_v1(lockfile) == normalize_conda_lock_v1(reference)

    # TODO: conda's context is not reset when EnvironmentExportNotSupported is raised?
    reset_context()
