from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from ruamel.yaml import YAML

from conda_lockfiles.constants import PIXI_LOCK_FILE
from conda_lockfiles.dumpers import rattler_lock
from conda_lockfiles.exceptions import EnvironmentExportNotSupported

from .. import SINGLE_PACKAGE_ENV, SINGLE_PACKAGE_NO_URL_ENV

if TYPE_CHECKING:
    from pathlib import Path


def test_export_to_rattler_lock_v6(tmp_path: Path) -> None:
    package_url = (
        "https://conda.anaconda.org/conda-forge/noarch/python_abi-3.13-7_cp313.conda"
    )

    lockfile_path = tmp_path / PIXI_LOCK_FILE
    rattler_lock.export_to_rattler_lock_v6(str(SINGLE_PACKAGE_ENV), str(lockfile_path))
    assert lockfile_path.exists()

    data = YAML().load(lockfile_path)

    assert data["version"] == 6

    # environments object
    assert "environments" in data
    assert "default" in data["environments"]
    default_env = data["environments"]["default"]
    assert "channels" in default_env
    assert "conda-forge" in default_env["channels"][0]["url"]
    assert "packages" in default_env
    subdirs_packages = tuple(default_env["packages"].values())
    assert len(subdirs_packages) == 1
    subdir_packages = subdirs_packages[0]
    assert len(subdir_packages) == 1
    assert subdir_packages[0]["conda"] == package_url

    # packages object
    assert "packages" in data
    packages = data["packages"]
    assert len(packages) == 1
    package = packages[0]
    assert package["conda"] == package_url
    assert (
        package["sha256"]
        == "0595134584589064f56e67d3de1d8fcbb673a972946bce25fb593fb092fdcd97"
    )
    assert package["md5"] == "e84b44e6300f1703cb25d29120c5b1d8"
    assert package["license"] == "BSD-3-Clause"
    assert package["size"] == 6988
    assert "python 3.13.* *_cp313" in package["constrains"]


def test_export_to_rattler_lock_v6_no_url(tmp_path: Path) -> None:
    lockfile_path = tmp_path / PIXI_LOCK_FILE
    with pytest.raises(EnvironmentExportNotSupported):
        rattler_lock.export_to_rattler_lock_v6(
            str(SINGLE_PACKAGE_NO_URL_ENV), str(lockfile_path)
        )
