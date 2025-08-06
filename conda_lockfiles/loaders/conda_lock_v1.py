from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from conda.base.context import context
from conda.common.io import dashlist
from conda.models.channel import Channel
from conda.models.environment import Environment, EnvironmentConfig
from conda.plugins.types import EnvironmentSpecBase

from ..dumpers.conda_lock_v1 import CONDA_LOCK_FILE
from .base import load_yaml
from .records_from_urls import records_from_conda_urls

if TYPE_CHECKING:
    from typing import Any, ClassVar, Final

    from conda.common.path import PathType


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
    metadata: dict[str, Any],
    package: list[dict[str, Any]],
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
        config=config,
        explicit_packages=records_from_conda_urls(explicit_packages),
        external_packages=external_packages,
    )


def _conda_lock_v1_package_to_record_overrides(
    *,
    manager: str,
    url: str,
    dependencies: dict[str, str] = {},
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
    format: ClassVar[str] = "conda-lock-v1"
    extensions: ClassVar[set[str]] = {".yml", ".yaml"}
    detection_supported: ClassVar[bool] = True

    def __init__(self, path: PathType):
        self.path = Path(path).resolve()

    def can_handle(self) -> bool:
        return (
            self.path.name == CONDA_LOCK_FILE
            and self.path.exists()
            and load_yaml(self.path)["version"] == 1
        )

    @property
    def env(self) -> Environment:
        return _conda_lock_v1_to_env(
            platform=context.subdir,
            **load_yaml(self.path),
        )
