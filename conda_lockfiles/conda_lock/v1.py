from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from conda.base.context import context
from conda.common.io import dashlist
from conda.common.serialize import yaml_safe_dump
from conda.exceptions import CondaValueError
from conda.models.channel import Channel
from conda.models.environment import Environment, EnvironmentConfig
from conda.models.match_spec import MatchSpec
from conda.plugins.types import EnvironmentSpecBase
from ruamel.yaml import YAMLError

from .. import __version__
from ..load_yaml import load_yaml
from ..records_from_conda_urls import records_from_conda_urls
from ..validate_urls import validate_urls

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any, ClassVar, Final, Literal, NotRequired, TypedDict

    from conda.common.path import PathType
    from conda.models.records import PackageRecord

    class CondaLockV1HashType(TypedDict):
        md5: NotRequired[str]
        sha256: NotRequired[str]

    CondaLockV1DependenciesType = dict[str, str]

    class CondaLockV1PackageType(TypedDict):
        name: str
        version: str
        manager: Literal["conda", "pypi"]
        platform: str
        dependencies: CondaLockV1DependenciesType
        url: str
        hash: CondaLockV1HashType
        category: str
        optional: bool

    class CondaLockV1ChannelType(TypedDict):
        url: str
        used_env_vars: list

    class CondaLockV1MetadataType(TypedDict):
        content_hash: dict[str, str]
        channels: list[CondaLockV1ChannelType]
        platforms: list[str]
        sources: list[str]

    CondaLockV1ManagerType = Literal["conda", "pypi"]


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

#: Mapping of supported package types (as used in the lockfile) to package
#: managers (as used in the environment)
PACKAGE_TYPES: Final = {
    "conda": "conda",
    "pip": "pypi",
}


def _record_to_dict(
    record: PackageRecord,
    platform: str,
) -> CondaLockV1PackageType:
    dependencies = {}
    for dep in record.depends:
        ms = MatchSpec(dep)
        version = ms.version.spec_str if ms.version is not None else ""
        dependencies[ms.name] = version
    _hash: CondaLockV1HashType = {}
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


def _to_dict(envs: Iterable[Environment]) -> dict[str, Any]:
    for env in envs:
        validate_urls(env, FORMAT)

    timestamp = datetime.now(timezone.utc).strftime(TIMESTAMP)
    packages: list[CondaLockV1PackageType] = [
        _record_to_dict(pkg, platform)
        for pkg, platform in sorted(
            # canonical order: sorted by platform/subdir then by name
            ((pkg, env.platform) for env in envs for pkg in env.explicit_packages),
            key=lambda pkg_platform: (pkg_platform[1], pkg_platform[0].url),
        )
    ]

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
            "platforms": sorted(env.platform for env in envs),
            "sources": [""],
            "time_metadata": {"created_at": timestamp},
            "custom_metadata": {"created_by": f"conda-lockfiles {__version__}"},
        },
        "package": packages,
    }


def multiplatform_export(envs: Iterable[Environment]) -> str:
    """Export Environment to conda-lock v1 format."""
    env_dict = _to_dict(envs)
    try:
        return yaml_safe_dump(env_dict)
    except YAMLError as e:
        raise CondaValueError(
            f"Failed to export environment to conda-lock v1 format: {e}"
        ) from e


def _conda_lock_v1_to_env(
    platform: str = context.subdir,
    *,
    # conda-lock.yml fields
    version: int,
    metadata: CondaLockV1MetadataType,
    package: list[CondaLockV1PackageType],
    **kwargs,
) -> Environment:
    if version != 1:
        raise ValueError(f"Unsupported version: {version}")
    elif kwargs:
        raise ValueError(f"Unexpected keyword arguments: {dashlist(kwargs)}")
    elif platform not in metadata["platforms"]:
        raise ValueError(
            f"Lockfile does not list packages for platform {platform}. "
            f"Available platforms: {dashlist(sorted(metadata['platforms']))}."
        )

    channels = metadata["channels"]
    config = EnvironmentConfig(
        channels=tuple(Channel(channel["url"]).canonical_name for channel in channels),
    )

    explicit_packages: dict[str, dict[str, Any]] = {}
    external_packages: dict[str, list[str]] = {}
    for pkg in package:
        # packages to ignore
        if pkg["platform"] != platform:
            continue
        if pkg["category"] != "main":
            continue
        if pkg["optional"]:
            continue
        if not (url := pkg.get("url")):
            continue

        # group packages by manager
        if (manager := pkg["manager"]) == "conda":
            explicit_packages[url] = _conda_lock_v1_package_to_record_overrides(**pkg)
        else:
            try:
                key = PACKAGE_TYPES[manager]
            except KeyError:
                raise ValueError(f"Unknown package type: {manager}")
            external_packages.setdefault(key, []).append(url)

    return Environment(
        prefix=context.target_prefix,
        platform=platform,
        config=config,
        explicit_packages=records_from_conda_urls(explicit_packages),
        external_packages=external_packages,
    )


def _conda_lock_v1_package_to_record_overrides(
    *,
    manager: CondaLockV1ManagerType,
    url: str,
    dependencies: CondaLockV1DependenciesType,
    platform: str,
    **kwargs,
) -> dict[str, Any]:
    if manager != "conda":
        raise ValueError(f"Unsupported manager: {manager}")
    # ignore url
    return {
        # dependencies are converted to a list of strings
        "depends": [f"{name} {version}" for name, version in dependencies.items()],
        # platform is renamed to subdir
        "subdir": platform,
        # other fields are passed through
        **kwargs,
    }


class CondaLockV1Loader(EnvironmentSpecBase):
    detection_supported: ClassVar[bool] = True

    def __init__(self, path: PathType):
        self.path = Path(path).resolve()

    def can_handle(self) -> bool:
        return (
            self.path.name in DEFAULT_FILENAMES
            and self.path.exists()
            and self._data["version"] == 1
        )

    @property
    def _data(self) -> dict[str, Any]:
        return load_yaml(self.path)

    @property
    def env(self) -> Environment:
        return _conda_lock_v1_to_env(platform=context.subdir, **self._data)
