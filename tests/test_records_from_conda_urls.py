from __future__ import annotations

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
