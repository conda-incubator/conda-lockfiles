from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, overload

from conda.base.context import context
from conda.common.io import dashlist
from conda.models.channel import Channel
from conda.models.environment import Environment, EnvironmentConfig
from conda.plugins.types import EnvironmentSpecBase

from ..constants import PIXI_LOCK_FILE
from .base import load_yaml
from .records_from_urls import records_from_conda_urls

if TYPE_CHECKING:
    from typing import Any, Final, Literal, TypedDict

    from conda.common.path import PathType

    class RattlerLockV6CondaKeyType(TypedDict):
        conda: str

    class RattlerLockV6PypiKeyType(TypedDict):
        pypi: str

    class RattlerLockV6OverrideKeysType(TypedDict):
        sha256: str
        md5: str
        license: str
        size: int
        timestamp: int

    class RattlerLockV6CondaPackageType(
        RattlerLockV6CondaKeyType, RattlerLockV6OverrideKeysType
    ): ...

    class RattlerLockV6PypiPackageType(
        RattlerLockV6PypiKeyType, RattlerLockV6OverrideKeysType
    ): ...

    class RattlerLockV6UrlKeyType(TypedDict):
        url: str

    class RattlerLockV6EnvironmentType(TypedDict):
        channels: list[RattlerLockV6UrlKeyType]
        packages: dict[
            str, list[RattlerLockV6CondaPackageType | RattlerLockV6PypiPackageType]
        ]


#: Supported package types
PACKAGE_TYPES: Final = {"pypi", "conda"}


def _rattler_lock_v6_to_env(
    name: str = "default",
    platform: str = context.subdir,
    *,
    # pixi.lock fields
    version: int,
    environments: dict[str, RattlerLockV6EnvironmentType],
    packages: list[RattlerLockV6CondaPackageType | RattlerLockV6PypiPackageType],
    **kwargs,
):
    if version != 6:
        raise ValueError(f"Unsupported version: {version}")
    elif kwargs:
        raise ValueError(f"Unexpected keyword arguments: {dashlist(kwargs)}")
    elif not (environment := environments.get(name, None)):
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

    lookup = {_get_package_key(pkg): pkg for pkg in packages}

    explicit_packages: dict[str, RattlerLockV6OverrideKeysType] = {}
    external_packages: dict[str, list[str]] = {}
    for pkg in environment["packages"][platform]:
        manager, url = (key := _get_package_key(pkg))
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


@overload
def _get_package_key(
    package: RattlerLockV6CondaPackageType,
) -> tuple[Literal["conda"], str]: ...


@overload
def _get_package_key(
    package: RattlerLockV6PypiPackageType,
) -> tuple[Literal["pypi"], str]: ...


def _get_package_key(package):
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
) -> RattlerLockV6OverrideKeysType:
    # ignore conda (url)
    # other fields are passed through
    return kwargs  # type: ignore


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
    def _data(self) -> dict[str, Any]:
        return load_yaml(self.path)

    @property
    def env(self) -> Environment:
        return _rattler_lock_v6_to_env(**self._data)
