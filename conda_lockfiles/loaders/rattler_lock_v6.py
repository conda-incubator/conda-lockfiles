from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from conda.base.context import context
from conda.common.io import dashlist
from conda.models.channel import Channel
from conda.models.environment import Environment, EnvironmentConfig
from conda.plugins.types import EnvironmentSpecBase

from ..constants import PIXI_LOCK_FILE
from .base import load_yaml
from .records_from_conda_urls import records_from_conda_urls

if TYPE_CHECKING:
    from typing import Any, Final

    from conda.common.path import PathType


#: Supported package types
PACKAGE_TYPES: Final = {"pypi"}


def _rattler_lock_v6_to_env(
    name: str = "default",
    platform: str = context.subdir,
    *,
    # pixi.lock fields
    version: int,
    environments: dict[str, Any],
    packages: list[dict[str, Any]],
    **kwargs,
):
    if version != 6:
        raise ValueError(f"Unsupported version: {version}")
    elif kwargs:
        raise ValueError(f"Unexpected keyword arguments: {dashlist(kwargs)}")
    elif environment := environments.get(name, None):
        raise ValueError(
            f"Environment '{name}' not found. "
            f"Available environments: {dashlist(sorted(environments))}"
        )
    elif platform not in environment["packages"]:
        raise ValueError(
            f"Lockfile does not list packages for platform {platform}. "
            f"Available platforms: {dashlist(sorted(environment['packages']))}."
        )

    channels = environment["channels"]
    config = EnvironmentConfig(
        channels=[Channel.from_url(channel["url"]) for channel in channels],
    )

    lookup = {_get_package_hash(pkg): pkg for pkg in packages}

    explicit_packages: dict[str, dict[str, Any]] = {}
    external_packages: dict[str, list[str]] = {}
    for pkg in environment["packages"][platform]:
        manager, url = (key := _get_package_hash(pkg))
        if key not in lookup:
            raise ValueError(f"Unknown package: {pkg}")
        elif manager == "conda":
            explicit_packages[url] = _rattler_lock_v6_package_to_record_overrides(**pkg)
        else:
            external_packages.setdefault(manager, []).append(url)

    return Environment(
        config=config,
        explicit_packages=records_from_conda_urls(explicit_packages),
        external_packages=external_packages,
    )


def _get_package_hash(package: dict[str, Any]) -> tuple[str, str]:
    managers = PACKAGE_TYPES.intersection(package)
    if len(managers) > 1:
        raise ValueError(f"Multiple package types: {dashlist(sorted(managers))}")
    elif not managers:
        raise ValueError(f"Unknown package type: {package}")
    else:
        manager = managers.pop()
        return (manager, package[manager])


def _rattler_lock_v6_package_to_record_overrides(
    *,
    conda: str,
    **kwargs,
) -> dict[str, Any]:
    # ignore conda (url)
    return {
        # other fields are passed through
        **kwargs,
    }


class RattlerLockV6Loader(EnvironmentSpecBase):
    def __init__(self, path: PathType):
        self.path = Path(path).resolve()

    def can_handle(self) -> bool:
        return (
            self.path.name == PIXI_LOCK_FILE
            and self.path.exists()
            and load_yaml(self.path)["version"] == 6
        )

    @property
    def env(self) -> Environment:
        return _rattler_lock_v6_to_env(**load_yaml(self.path))
