from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from conda.base.context import context
from conda.common.io import dashlist
from conda.models.channel import Channel
from conda.models.environment import Environment, EnvironmentConfig
from conda.plugins.types import EnvironmentSpecBase

from ...load_yaml import load_yaml
from ...records_from_conda_urls import records_from_conda_urls
from .dumper import CONDA_LOCK_FILE, DEFAULT_FILENAMES, FORMAT

if TYPE_CHECKING:
    from typing import Any, ClassVar, Final, Literal, NotRequired, TypedDict

    from conda.common.path import PathType

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
FORMAT

#: The filename of the conda-lock v1 format.
CONDA_LOCK_FILE

#: Default filenames for the conda-lock v1 format.
DEFAULT_FILENAMES

#: Mapping of supported package types (as used in the lockfile) to package
#: managers (as used in the environment)
PACKAGE_TYPES: Final = {
    "conda": "conda",
    "pip": "pypi",
}


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
        channels=[Channel.from_url(channel["url"]) for channel in channels],
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
