from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

from conda.base.context import context
from conda.common.io import dashlist
from conda.common.serialize import yaml_safe_dump
from conda.exceptions import CondaValueError
from conda.models.channel import Channel
from conda.models.environment import Environment, EnvironmentConfig
from conda.plugins.types import EnvironmentSpecBase
from pydantic import BaseModel, Field, ValidationError, computed_field, field_validator
from ruamel.yaml import YAMLError

from ..exceptions import format_validation_errors
from ..load_yaml import load_yaml
from ..records_from_conda_urls import records_from_conda_urls
from ..validate_urls import validate_urls

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any, ClassVar, Final, TypedDict

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

#: Supported package types.
PackageType = Literal["conda", "pypi"]


# Pydantic Models
class RattlerLockV6Channel(BaseModel):
    """A channel specification in a rattler lock file."""

    url: str


class RattlerLockV6PackageReference(BaseModel):
    """A reference to a package in an environment (just the URL)."""

    conda: str | None = None
    pypi: str | None = None

    @field_validator("conda", "pypi")
    @classmethod
    def check_at_least_one(cls, v, info):
        """Ensure at least one package manager is specified."""
        if not v and not info.data.get("conda") and not info.data.get("pypi"):
            raise ValueError("Either 'conda' or 'pypi' must be specified")

        if v and info.data.get("conda") and info.data.get("pypi"):
            raise ValueError("Either 'conda' or 'pypi' must be specified, not both")

        return v

    @computed_field(repr=False)
    @property
    def package_type(self) -> PackageType:
        """Infer package type from `conda` and `pypi` fields"""
        if self.conda:
            return "conda"
        elif self.pypi:
            return "pypi"
        else:
            raise ValueError("Either 'conda' or 'pypi' must be specified")


class RattlerLockV6Package(BaseModel):
    """Full package definition with metadata in the packages list."""

    # Required field
    conda: str | None = None
    pypi: str | None = None

    # Optional metadata fields
    sha256: str | None = None
    md5: str | None = None
    license: str | None = None
    license_family: str | None = None
    size: int | None = None
    timestamp: int | None = None
    depends: list[str] | None = None
    constrains: list[str] | None = None
    features: str | None = None
    track_features: list[str] | None = None
    python_site_packages_path: str | None = None

    @field_validator("conda", "pypi")
    @classmethod
    def check_at_least_one_package_type(cls, v, info):
        """Ensure at least one package manager is specified."""
        if not v and not info.data.get("conda") and not info.data.get("pypi"):
            raise ValueError("Either 'conda' or 'pypi' must be specified")

        if v and info.data.get("conda") and info.data.get("pypi"):
            raise ValueError("Either 'conda' or 'pypi' must be specified, not both")
        return v


class RattlerLockV6Environment(BaseModel):
    """An environment specification in a rattler lock file."""

    channels: list[RattlerLockV6Channel]
    packages: dict[str, list[RattlerLockV6PackageReference]] = Field(
        description="Mapping of platform names to package lists"
    )


class RattlerLockV6(BaseModel):
    """The root structure of a rattler lock v6 file."""

    version: int = Field(description="Lock file format version, must be 6")
    environments: dict[str, RattlerLockV6Environment] = Field(
        description="Mapping of environment names to environment specifications"
    )
    packages: list[RattlerLockV6Package] = Field(
        description="Complete list of packages with full metadata"
    )

    @field_validator("version")
    @classmethod
    def check_version(cls, v):
        """Ensure version is 6."""
        if v != 6:
            raise ValueError(f"Unsupported version: {v}, expected 6")
        return v

    @field_validator("environments")
    @classmethod
    def check_default_env(cls, v):
        """Ensure default environment exists."""
        if "default" not in v:
            raise ValueError("Lock file must contain a 'default' environment")
        return v

    def get_package_metadata(
        self, url: str, package_type: PackageType
    ) -> RattlerLockV6Package | None:
        """
        Get package by searching with ``url`` and ``package_type``
        """
        try:
            return next(
                filter(
                    lambda pkg: getattr(pkg, package_type, None) == url, self.packages
                )
            )
        except StopIteration:
            raise ValueError(f"Could not find package with url '{url}' in lockfile")

    def as_conda_env(
        self, name: str = "default", platform: str = context.subdir
    ) -> Environment:
        """
        Render lockfile as a conda environment
        """
        # validate `name` and `platform` arguments
        if not (environment := self.environments.get(name, None)):
            raise ValueError(
                f"Environment '{name}' not found. \n"
                f"Available environments: {dashlist(sorted(self.environments.keys()))}"
            )
        if platform not in environment.packages:
            raise ValueError(
                f"Lockfile does not list packages for platform {platform}.\n"
                f"Available platforms: {dashlist(sorted(environment.packages))}."
            )

        channels = environment.channels
        config = EnvironmentConfig(
            channels=tuple(Channel(channel.url).canonical_name for channel in channels),
        )

        explicit_packages = {
            getattr(pkg, "conda"): self.get_package_metadata(
                getattr(pkg, "conda"), pkg.package_type
            ).model_dump()
            for pkg in environment.packages.get(platform)
            if pkg.package_type == "conda"
        }

        external_packages = {
            getattr(pkg, pkg.package_type): self.get_package_metadata(
                getattr(pkg, pkg.package_type), pkg.package_type
            ).model_dump()
            for pkg in environment.packages.get(platform)
            if pkg.package_type != "conda"
        }

        return Environment(
            prefix=context.target_prefix,
            platform=platform,
            config=config,
            explicit_packages=records_from_conda_urls(explicit_packages),
            external_packages=external_packages,
        )

    @classmethod
    def from_conda_envs(cls, envs: Iterable[Environment]) -> RattlerLockV6:
        """
        Create a RattlerLockV6 lockfile from conda Environment objects.

        :param envs: Iterable of conda Environment objects
            (typically multiple platforms)
        :return: RattlerLockV6 Pydantic model instance
        """
        # Convert to list to allow multiple iterations
        env_list = list(envs)

        # Validate URLs for all environments
        for env in env_list:
            validate_urls(env, FORMAT)

        # Build per-platform package references
        seen = set()
        packages: list[RattlerLockV6Package] = []
        platforms: dict[str, list[RattlerLockV6PackageReference]] = {
            platform: [] for platform in sorted(env.platform for env in env_list)
        }

        # TODO: Add support for external_packages (PyPI packages)
        # Currently only exports conda packages from env.explicit_packages

        # Process packages in canonical order (sorted by name, then platform)
        for pkg, platform in sorted(
            ((pkg, env.platform) for env in env_list for pkg in env.explicit_packages),
            key=lambda pkg_platform: (pkg_platform[0].name, pkg_platform[1]),
        ):
            # Add package reference to this platform
            platforms[platform].append(RattlerLockV6PackageReference(conda=pkg.url))

            # Deduplicate: only add to packages list once
            if pkg.url in seen:
                continue
            packages.append(_record_to_package(pkg))
            seen.add(pkg.url)

        # Build channel list from first environment
        # (all environments should have same channels for multiplatform export)
        env = env_list[0]
        channels = [
            RattlerLockV6Channel(url=channel) for channel in env.config.channels
        ]

        # Build environment
        default_env = RattlerLockV6Environment(channels=channels, packages=platforms)

        # Construct and return RattlerLockV6 instance
        return cls(version=6, environments={"default": default_env}, packages=packages)


def _record_to_package(record: PackageRecord) -> RattlerLockV6Package:
    """
    Convert a conda PackageRecord to a RattlerLockV6Package Pydantic model.

    :param record: Conda package record
    :return: RattlerLockV6Package with metadata
    """
    # Build kwargs for RattlerLockV6Package constructor
    kwargs = {"conda": record.url}

    # Add optional metadata fields (same as previous _record_to_dict logic)
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
            kwargs[field] = data

    return RattlerLockV6Package(**kwargs)


def multiplatform_export(envs: Iterable[Environment]) -> str:
    """Export Environment to rattler lock format."""
    lockfile = RattlerLockV6.from_conda_envs(envs)
    try:
        # Exclude None values and computed fields from serialization
        return yaml_safe_dump(
            lockfile.model_dump(
                exclude_none=True,
                mode="python",
                exclude={
                    "packages": {"__all__": {"package_type"}},
                    "environments": {
                        "__all__": {
                            "packages": {"__all__": {"__all__": {"package_type"}}}
                        }
                    },
                },
            )
        )
    except YAMLError as e:
        raise CondaValueError(
            f"Failed to export environment to rattler lock format: {e}"
        ) from e


class RattlerLockV6Loader(EnvironmentSpecBase):
    detection_supported: ClassVar[bool] = True

    def __init__(self, path: PathType):
        self.path = Path(path).resolve()
        self._model: RattlerLockV6 | None = None

    def can_handle(self) -> bool:
        """
        Attempts to validate loaded data as a rattler lock v6 specification.

        :raises ValueError: Raised when validation fails
        """
        # Check filename first (before trying to load the file)
        if self.path.name not in DEFAULT_FILENAMES:
            raise ValueError(
                f"Invalid filename: {self.path}; please choose one from: "
                f"{DEFAULT_FILENAMES}"
            )
        if not self.path.exists():
            raise ValueError(f"File not found: {self.path}")

        return self._validate_model()

    def _validate_model(self) -> bool:
        """
        Attempt to load model

        :returns: indicates successful load
        :raises ValueError: raised when validation fails
        """
        try:
            self._model = RattlerLockV6.model_validate(self._data)
            return True
        except ValidationError as e:
            formatted_errors = format_validation_errors(e.errors(), self.path)
            raise ValueError(formatted_errors) from e

    @property
    def _data(self) -> dict[str, Any]:
        return load_yaml(self.path)

    @property
    def env(self) -> Environment:
        try:
            if self._model is None:
                self._validate_model()
            return self._model.as_conda_env()
        except ValueError as e:
            raise CondaValueError(f"\n\nUnable to create environment: {e}") from e
