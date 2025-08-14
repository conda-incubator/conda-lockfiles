from __future__ import annotations

from typing import TYPE_CHECKING

from ruamel.yaml import YAML

from conda_lockfiles.dumpers import conda_lock_v1

from .. import SINGLE_PACKAGE_ENV

if TYPE_CHECKING:
    from pathlib import Path


def test_export_to_conda_lock_v1(tmp_path: Path) -> None:
    lockfile_path = tmp_path / conda_lock_v1.CONDA_LOCK_FILE
    conda_lock_v1.export_to_conda_lock_v1(str(SINGLE_PACKAGE_ENV), str(lockfile_path))
    assert lockfile_path.exists()

    data = YAML().load(lockfile_path)

    assert data["version"] == 1

    # metadata object
    assert "metadata" in data
    metadata = data["metadata"]
    assert "channels" in metadata
    assert len(metadata["channels"]) == 1
    assert "conda-forge" in metadata["channels"][0]["url"]
    assert "platforms" in metadata
    # the contents of platforms depends on the test platform
    assert "time_metadata" in metadata
    assert "custom_metadata" in metadata
    assert metadata["custom_metadata"]["created_by"] == "conda-lockfiles"

    # package object
    assert "package" in data
    package = data["package"]
    assert len(package) == 1
    pkg = package[0]
    assert pkg["name"] == "python_abi"
    assert pkg["version"] == "3.13"
    assert pkg["manager"] == "conda"
    assert "platform" in pkg
    assert len(pkg["dependencies"]) == 0
    assert (
        pkg["url"]
        == "https://conda.anaconda.org/conda-forge/noarch/python_abi-3.13-7_cp313.conda"
    )
    assert "hash" in pkg
    hash_ = pkg["hash"]
    assert (
        hash_["sha256"]
        == "0595134584589064f56e67d3de1d8fcbb673a972946bce25fb593fb092fdcd97"
    )
    assert hash_["md5"] == "e84b44e6300f1703cb25d29120c5b1d8"
    assert pkg["category"] == "main"
    assert not pkg["optional"]
