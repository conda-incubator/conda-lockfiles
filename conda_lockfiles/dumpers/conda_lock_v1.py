from __future__ import annotations

import datetime
import sys
from contextlib import nullcontext
from typing import TYPE_CHECKING

from conda.base.context import context
from conda.common.serialize import yaml_safe_dump
from conda.core.prefix_data import PrefixData
from conda.exceptions import CondaValueError
from conda.models.match_spec import MatchSpec
from ruamel.yaml import YAML, YAMLError

if TYPE_CHECKING:
    from typing import Any, Final

    from conda.models.environment import Environment
    from conda.models.records import PackageRecord


#: The name of the conda-lock v1 format.
FORMAT: Final = "conda-lock-v1"

#: Aliases for the conda-lock v1 format.
ALIASES: Final = ()

#: The filename of the conda-lock v1 format.
CONDA_LOCK_FILE: Final = "conda-lock.yml"

#: Default filenames for the conda-lock v1 format.
DEFAULT_FILENAMES: Final = (CONDA_LOCK_FILE,)

#: The timestamp format for the conda-lock v1 format.
TIMESTAMP: Final = "%Y-%m-%dT%H:%M:%SZ"


def _record_to_dict(
    record: PackageRecord,
    platform: str,
) -> dict[str, Any]:
    dependencies = {}
    for dep in record.depends:
        ms = MatchSpec(dep)
        version = ms.version.spec_str if ms.version is not None else ""
        dependencies[ms.name] = version
    _hash = {}
    if record.md5:
        _hash["md5"] = record.md5
    if record.sha256:
        _hash["sha256"] = record.sha256
    return {
        "name": record.name,
        "version": record.version,
        "manager": "conda",
        "platform": platform,
        "dependencies": dependencies,
        "url": record.url,
        "hash": _hash,
        "category": "main",
        "optional": False,
    }


def _to_dict(env: Environment) -> dict[str, Any]:
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime(TIMESTAMP)
    return {
        "version": 1,
        "metadata": {
            "content_hash": {},
            "channels": [
                {
                    "url": getattr(channel, "canonical_name", None),
                    "used_env_vars": [],
                }
                for channel in env.config.channels
            ],
            "platforms": [env.platform],
            "sources": [""],
            "time_metadata": {"created_at": timestamp},
            "custom_metadata": {"created_by": "conda-lockfiles"},
        },
        "package": [
            _record_to_dict(pkg, env.platform)
            for pkg in sorted(env.explicit_packages, key=lambda pkg: pkg.name)
        ],
    }


def export(env: Environment) -> str:
    """Export Environment to conda-lock v1 format."""
    env_dict = _to_dict(env)
    try:
        return yaml_safe_dump(env_dict)
    except YAMLError as e:
        raise CondaValueError(
            f"Failed to export environment to conda-lock v1 format: {e}"
        ) from e


# deprecated, keep for testing
def export_to_conda_lock_v1(prefix: str, lockfile_path: str | None) -> None:
    prefix_data = PrefixData(prefix)
    packages = [_record_to_dict(p, context.subdir) for p in prefix_data.iter_records()]
    channel_urls = {(p.schannel) for p in prefix_data.iter_records()}
    metadata = {
        "content_hash": {},
        "channels": [{"url": url, "used_env_vars": []} for url in channel_urls],
        "platforms": [context.subdir],
        "sources": [""],
        "time_metadata": {
            "created_at": datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
        },
        "custom_metadata": {
            "created_by": "conda-lockfiles",
        },
    }
    output = {
        "version": 1,
        "metadata": metadata,
        "package": sorted(packages, key=lambda x: x["name"]),
    }
    with open(lockfile_path, "w") if lockfile_path else nullcontext(sys.stdout) as fh:
        YAML().dump(output, stream=fh)
