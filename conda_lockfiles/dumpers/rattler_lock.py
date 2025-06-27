from __future__ import annotations

import sys
from contextlib import nullcontext
from typing import TYPE_CHECKING

from conda.base.context import context
from conda.core.prefix_data import PrefixData
from ruamel.yaml import YAML

from ..exceptions import EnvironmentExportNotSupported

if TYPE_CHECKING:
    from typing import Any

    from conda.models.records import PackageRecord


LOCKFILE_FORMAT = "pixi"


def _record_to_rattler_lock_v6(record: PackageRecord) -> dict[str, Any]:
    if record.url is None:
        raise EnvironmentExportNotSupported(LOCKFILE_FORMAT)
    package = {
        "conda": str(record.url),
    }
    # add relevent non-empty fields that rattler_lock includes in v6 lockfiles
    # https://github.com/conda/rattler/blob/rattler_lock-v0.23.5/crates/rattler_lock/src/parse/models/v6/conda_package_data.rs#L46
    fields = [
        # channel, subdir, name, build and version can be determined from the URL
        "sha256",
        "md5",
        "depends",
        "constrains",
        "features",
        "track_features",
        "license",
        "license_family",
        "size",
        # libmamba-conda-solver does not record the repodata timestamp,
        # do not include this field, see:
        # https://github.com/conda/conda-libmamba-solver/issues/673
        # "timestamp",
        "python_site_packages_path",
    ]
    for field in fields:
        if data := record.get(field, None):
            package[field] = data
    return package


def export_to_rattler_lock_v6(prefix: str, lockfile_path: str | None) -> None:
    prefix_data = PrefixData(prefix)
    unique_channels = {(record.channel) for record in prefix_data.iter_records()}
    if None in unique_channels:
        raise EnvironmentExportNotSupported(LOCKFILE_FORMAT)
    channels = sorted([{"url": str(url)} for url in unique_channels])
    if None in channels:
        raise Exception
    packages = sorted(
        [_record_to_rattler_lock_v6(record) for record in prefix_data.iter_records()],
        key=lambda x: x["conda"],
    )
    env_subdir_pkgs = [{"conda": package["conda"]} for package in packages]
    environments = {
        "default": {
            "channels": channels,
            "packages": {
                context.subdir: env_subdir_pkgs,
            },
        }
    }
    output = {
        "version": 6,
        "environments": environments,
        "packages": packages,
    }
    with open(lockfile_path, "w") if lockfile_path else nullcontext(sys.stdout) as fh:
        YAML().dump(output, stream=fh)
