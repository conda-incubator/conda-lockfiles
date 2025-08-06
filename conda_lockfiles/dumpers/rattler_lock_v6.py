from __future__ import annotations

import sys
from contextlib import nullcontext
from typing import TYPE_CHECKING

from conda.base.context import context
from conda.common.serialize.yaml import yaml_safe_dump
from conda.core.prefix_data import PrefixData
from conda.exceptions import CondaValueError
from ruamel.yaml import YAML, YAMLError

from ..exceptions import EnvironmentExportNotSupported

if TYPE_CHECKING:
    from typing import Any, Final

    from conda.models.environment import Environment
    from conda.models.records import PackageRecord


#: The name of the rattler lock format.
FORMAT: Final = "pixi"

#: Aliases for the rattler lock format.
ALIASES: Final = ("rattler-lock",)

#: Default filenames for the rattler lock format.
DEFAULT_FILENAMES: Final = ("rattler-lock.yaml", "rattler-lock.yml")


def _record_to_dict(record: PackageRecord) -> dict[str, Any]:
    if record.url is None:
        raise EnvironmentExportNotSupported(FORMAT)
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


def _to_dict(env: Environment) -> dict[str, Any]:
    packages = sorted(env.explicit_packages, key=lambda package: package.url)
    return {
        "version": 6,
        "environments": {
            "default": {
                "channels": [{"url": str(channel)} for channel in env.config.channels],
                "packages": {
                    context.subdir: [{"conda": package.url} for package in packages]
                },
            },
        },
        "packages": [_record_to_dict(package) for package in packages],
    }


def export(env: Environment) -> str:
    """Export Environment to rattler lock format."""
    env_dict = _to_dict(env)
    try:
        return yaml_safe_dump(env_dict)
    except YAMLError as e:
        raise CondaValueError(
            f"Failed to export environment to rattler lock format: {e}"
        ) from e


# deprecated, keep for testing
def export_to_rattler_lock_v6(prefix: str, lockfile_path: str | None) -> None:
    prefix_data = PrefixData(prefix)
    unique_channels = {(record.channel) for record in prefix_data.iter_records()}
    if None in unique_channels:
        raise EnvironmentExportNotSupported(FORMAT)
    channels = sorted([{"url": str(url)} for url in unique_channels])
    packages = sorted(
        [_record_to_dict(record) for record in prefix_data.iter_records()],
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
