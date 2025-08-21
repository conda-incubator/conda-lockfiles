from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from conda.common.serialize import yaml_safe_dump
from conda.exceptions import CondaValueError
from conda.models.match_spec import MatchSpec
from ruamel.yaml import YAMLError

from ... import __version__
from ...validate_urls import validate_urls

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
    validate_urls(env, FORMAT)
    timestamp = datetime.now(timezone.utc).strftime(TIMESTAMP)
    return {
        "version": 1,
        "metadata": {
            "content_hash": {},
            "channels": [
                {
                    "url": channel,
                    "used_env_vars": [],
                }
                for channel in env.config.channels
            ],
            "platforms": [env.platform],
            "sources": [""],
            "time_metadata": {"created_at": timestamp},
            "custom_metadata": {"created_by": f"conda-lockfiles {__version__}"},
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
