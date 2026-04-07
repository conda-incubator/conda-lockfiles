from __future__ import annotations

import pytest
from conda.base.context import reset_context
from conda.exceptions import DryRunExit

from conda_lockfiles.records_from_conda_urls import records_from_conda_urls


def test_records_from_urls_and_metadata() -> None:
    md5 = "4222072737ccff51314b5ece9c7d6f5a"
    sha256 = "5aaa366385d716557e365f0a4e9c3fca43ba196872abbbe3d56bb610d131e192"
    license = "ONLY_IN_TEST"

    metadata_by_url = {
        "https://conda.anaconda.org/conda-forge/noarch/tzdata-2025b-h78e105d_0.conda": {
            "md5": md5,
            "sha256": sha256,
            "license": license,
        },
    }
    records = records_from_conda_urls(metadata_by_url)
    assert isinstance(records, tuple)
    assert len(records) == 1
    record = records[0]
    assert record.name == "tzdata"
    # set by passed metadata
    assert record.md5 == md5
    assert record.sha256 == sha256
    assert record.license == license
    # only known after downloading
    assert record.size == 122_968


#: Used in ``test_records_from_conda_urls_dry_run`` test as expected output
EXPECTED_DRY_RUN_OUTPUT = (
    "\nDry run would have fetched the following package records:\n"
    "- example/noarch::package==0.1.0=h396c80c_0[md5=edd329d7d3a4ab45dcf905899a7a6115,"
    "sha256=7c2df5721c742c2a47b2c8f960e718c930031663ac1174da67c1ed5999f7938c]\n"
    "- example/noarch::dependency==0.2.1=h536810c_0[md5=a9d86bc62f39b94c4661716624eb21"
    "b0,sha256=799cab4b6cde62f91f750149995d149bc9db525ec12595e8a1d91b9317f038b3]\n"
)


def test_records_from_conda_urls_dry_run(monkeypatch, capsys):
    """
    Ensure that the metadata_by_url is shown correctly when dry_run is True.

    Regression fix for: https://github.com/conda-incubator/conda-lockfiles/issues/109
    """
    monkeypatch.setenv("CONDA_CHANNEL_ALIAS", "https://example.com")

    reset_context(())

    metadata_by_url = {
        "https://example.com/example/noarch/package-0.1.0-h396c80c_0.conda": {
            "conda": (
                "https://example.com/example/noarch/package-0.1.0-h396c80c_0.conda"
            ),
            "sha256": (
                "7c2df5721c742c2a47b2c8f960e718c930031663ac1174da67c1ed5999f7938c"
            ),
            "md5": "edd329d7d3a4ab45dcf905899a7a6115",
        },
        "https://example.com/example/noarch/dependency-0.2.1-h536810c_0.conda": {
            "conda": (
                "https://example.com/example/noarch/dependency-0.2.1-h536810c_0.conda"
            ),
            "sha256": (
                "799cab4b6cde62f91f750149995d149bc9db525ec12595e8a1d91b9317f038b3"
            ),
            "md5": "a9d86bc62f39b94c4661716624eb21b0",
        },
    }

    with pytest.raises(DryRunExit):
        records_from_conda_urls(metadata_by_url, dry_run=True)

    out, err = capsys.readouterr()

    assert out == EXPECTED_DRY_RUN_OUTPUT
