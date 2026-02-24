from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, overload

from conda.base.context import context
from conda.common.io import dashlist
from conda.common.serialize import yaml_safe_dump
from conda.exceptions import CondaValueError
from conda.models.channel import Channel
from conda.models.environment import Environment, EnvironmentConfig
from conda.plugins.types import EnvironmentSpecBase
from ruamel.yaml import YAMLError

from ..load_yaml import load_yaml
from ..records_from_conda_urls import records_from_conda_urls
from ..validate_urls import validate_urls

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any, ClassVar, Final, Literal, TypedDict

    from conda.common.path import PathType
    from conda.models.records import PackageRecord

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


#: The name of the rattler lock v6 format.
FORMAT: Final = "rattler-lock-v6"

#: Aliases for the rattler lock v6 format.
ALIASES: Final = ("pixi-lock-v6",)

#: The filename of the rattler lock v6 format.
PIXI_LOCK_FILE: Final = "pixi.lock"

#: Default filenames for the rattler lock v6 format.
DEFAULT_FILENAMES: Final = (PIXI_LOCK_FILE,)

#: Supported package types.
PACKAGE_TYPES: Final = {"pypi", "conda"}


def _record_to_dict(record: PackageRecord) -> RattlerLockV6CondaPackageType:
    package = {"conda": record.url}
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


def _to_dict(envs: Iterable[Environment]) -> dict[str, Any]:
    for env in envs:
        validate_urls(env, FORMAT)

    seen = set()
    packages: list[RattlerLockV6CondaPackageType] = []
    platforms: dict[str, list[RattlerLockV6CondaKeyType]] = {
        platform: [] for platform in sorted(env.platform for env in envs)
    }
    for pkg, platform in sorted(
        # canonical order: sorted by name then by platform/subdir
        ((pkg, env.platform) for env in envs for pkg in env.explicit_packages),
        key=lambda pkg_platform: (pkg_platform[0].name, pkg_platform[1]),
    ):
        # list every package for every platform
        # (e.g., noarch packages are listed for every platform)
        platforms[platform].append({"conda": pkg.url})

        # packages list should only contain each package once
        # (e.g., noarch packages are deduplicated)
        if pkg.url in seen:
            continue
        packages.append(_record_to_dict(pkg))
        seen.add(pkg.url)

    return {
        "version": 6,
        "environments": {
            "default": {
                "channels": [{"url": channel} for channel in env.config.channels],
                "packages": platforms,
            },
        },
        "packages": packages,
    }


def multiplatform_export(envs: Iterable[Environment]) -> str:
    """Export Environment to rattler lock format."""
    env_dict = _to_dict(envs)
    try:
        return yaml_safe_dump(env_dict)
    except YAMLError as e:
        raise CondaValueError(
            f"Failed to export environment to rattler lock format: {e}"
        ) from e


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
        channels=tuple(Channel(channel["url"]).canonical_name for channel in channels),
    )

    lookup = {_get_package_key(pkg): pkg for pkg in packages}

    explicit_packages: dict[str, RattlerLockV6OverrideKeysType] = {}
    external_packages: dict[str, list[str]] = {}
    for pkg in environment["packages"][platform]:
        manager, url = (key := _get_package_key(pkg))
        try:
            pkg = lookup[key]
        except KeyError:
            raise ValueError(f"Unknown package: {pkg}")

        if manager == "conda":
            explicit_packages[url] = _rattler_lock_v6_package_to_record_overrides(**pkg)
        else:
            external_packages.setdefault(manager, []).append(url)

    return Environment(
        prefix=context.target_prefix,
        platform=platform,
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


def _validate_v6(data: dict[str, Any], path: Path) -> None:
    """
    Validate the rattler lock v6 specification.

    :raises ValueError: Raised when validation fails
    """
    if path.name not in DEFAULT_FILENAMES:
        raise ValueError(
            f"Invalid filename: {path}; please choose one from: {DEFAULT_FILENAMES}"
        )

    if not path.exists():
        raise ValueError(f"File does not exist: {path}")

    # Validate lockfile structure
    try:
        # Check version
        if data["version"] != 6:
            raise ValueError(f"File {path} has invalid version (!= 6)")

        # Check required fields exist and have correct types
        environments = data.get("environments")
        if not isinstance(environments, dict):
            raise ValueError(
                f"File {path} has version 6 but environments is not a mapping"
            )

        if "default" not in environments:
            raise ValueError(f"File {path} has version 6 but no default environment")

        default_env = environments["default"]
        if not isinstance(default_env, dict):
            raise ValueError(
                f"File {path} has version 6 but default environment is not a mapping"
            )

        if "channels" not in default_env or not isinstance(
            default_env["channels"], list
        ):
            raise ValueError(
                f"File {path} has version 6 but missing or invalid channels in default "
                "environment"
            )

        if "packages" not in default_env or not isinstance(
            default_env["packages"], dict
        ):
            raise ValueError(
                f"File {path} has version 6 but missing or invalid packages in default "
                "environment"
            )

        if not default_env["packages"]:
            raise ValueError(
                f"File {path} has version 6 but no packages in default environment"
            )

        # Check packages field exists and is a list
        if "packages" not in data or not isinstance(data["packages"], list):
            raise ValueError(
                f"File {path} has version 6 but missing or invalid packages list"
            )

    except (KeyError, TypeError) as e:
        raise ValueError(f"File {path} has version 6 but failed validation: {e}")


class RattlerLockV6Loader(EnvironmentSpecBase):
    detection_supported: ClassVar[bool] = True

    def __init__(self, path: PathType):
        self.path = Path(path).resolve()

    def can_handle(self) -> bool:
        """
        Attempts to validate loaded data as a rattler lock v6 specification.

        :raises ValueError: Raised when validation fails
        """
        # Check filename first (before trying to load the file)
        if self.path.name not in DEFAULT_FILENAMES:
            raise ValueError(
                "Invalid filename: {self.path}; please choose one from: "
                f"{DEFAULT_FILENAMES}"
            )

        try:
            _validate_v6(self._data, self.path)
            return True
        except (FileNotFoundError, YAMLError) as e:
            raise ValueError(f"Cannot load file {self.path}: {e}") from e

    @property
    def _data(self) -> dict[str, Any]:
        return load_yaml(self.path)

    @property
    def env(self) -> Environment:
        return _rattler_lock_v6_to_env(**self._data)
