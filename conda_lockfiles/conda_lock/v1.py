from __future__ import annotations

import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from conda.base.context import context
from conda.common.serialize import yaml_safe_dump
from conda.exceptions import CondaValueError
from conda.models.channel import Channel
from conda.models.environment import Environment, EnvironmentConfig
from conda.models.match_spec import MatchSpec
from conda.plugins.types import EnvironmentSpecBase
from pydantic import BaseModel, Field, ValidationError, field_validator
from ruamel.yaml import YAMLError

from .. import __version__
from ..exceptions import format_validation_errors
from ..load_yaml import load_yaml
from ..records_from_conda_urls import records_from_conda_urls
from ..validate_urls import validate_urls

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any, ClassVar, Final, Literal

    from conda.common.path import PathType
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

#: Mapping of supported package types (as used in the lockfile) to package
#: managers (as used in the environment)
PACKAGE_TYPES: Final = {
    "conda": "conda",
    "pip": "pypi",
}

PIP_EXPORT_WARNING: Final = (
    "This lockfile does not include the pip-installed packages "
    "in your environment.\n"
    "To fully reproduce this environment:\n"
    "  1. Identify the pip packages in your environment: conda list "
    "(look for 'pypi' channel)\n"
    "  2. Install the pip packages manually after applying the lockfile"
)


class CondaLockV1Hash(BaseModel):
    """Hash information for a package."""

    md5: str | None = None
    sha256: str | None = None


class CondaLockV1Package(BaseModel):
    """A package entry in the conda-lock v1 lockfile."""

    name: str
    version: str
    manager: Literal["conda", "pypi"]
    platform: str
    dependencies: dict[str, str] = Field(default_factory=dict)
    url: str
    hash: CondaLockV1Hash = Field(default_factory=CondaLockV1Hash)
    category: str = "main"
    optional: bool = False


class CondaLockV1Channel(BaseModel):
    """A channel specification in the metadata."""

    url: str
    used_env_vars: list[str] = Field(default_factory=list)


class CondaLockV1TimeMetadata(BaseModel):
    """Time metadata for the lockfile."""

    created_at: str


class CondaLockV1CustomMetadata(BaseModel):
    """Custom metadata for the lockfile."""

    created_by: str


class CondaLockV1Metadata(BaseModel):
    """Metadata section of the conda-lock v1 lockfile."""

    content_hash: dict[str, str] = Field(default_factory=dict)
    channels: list[CondaLockV1Channel]
    platforms: list[str]
    sources: list[str] = Field(default_factory=list)
    time_metadata: CondaLockV1TimeMetadata | None = None
    custom_metadata: CondaLockV1CustomMetadata | None = None

    @field_validator("platforms")
    @classmethod
    def check_platforms_not_empty(cls, v: list[str]) -> list[str]:
        """Ensure at least one platform is specified."""
        if not v:
            raise ValueError("At least one platform must be specified")
        return v


class CondaLockV1(BaseModel):
    """The root structure of a conda-lock v1 file."""

    version: int = Field(default=1)
    metadata: CondaLockV1Metadata
    package: list[CondaLockV1Package]

    @field_validator("version")
    @classmethod
    def check_version(cls, v: int) -> int:
        """Ensure version is 1."""
        if v != 1:
            raise ValueError(f"Unsupported version: {v}, expected 1")
        return v

    @classmethod
    def from_conda_envs(cls, envs: Iterable[Environment]) -> CondaLockV1:
        """
        Create a CondaLockV1 lockfile from conda Environment objects.

        :param envs: Iterable of conda Environment objects
            (typically multiple platforms)
        :return: CondaLockV1 Pydantic model instance
        """
        # Convert to list to allow multiple iterations
        env_list = list(envs)

        # Check for pip packages and warn
        for env in env_list:
            if env.external_packages.get("pip"):
                warnings.warn(PIP_EXPORT_WARNING)
            validate_urls(env, FORMAT)

        # Generate timestamp
        timestamp = datetime.now(timezone.utc).strftime(TIMESTAMP)

        # Build packages list (no deduplication for v1 format)
        packages: list[CondaLockV1Package] = [
            _record_to_package(pkg, platform)
            for pkg, platform in sorted(
                # canonical order: sorted by platform/subdir then by URL
                (
                    (pkg, env.platform)
                    for env in env_list
                    for pkg in env.explicit_packages
                ),
                key=lambda pkg_platform: (pkg_platform[1], pkg_platform[0].url),
            )
        ]

        # Build metadata from first environment
        # (all environments should have same channels for multiplatform export)
        env = env_list[0]
        channels = [
            CondaLockV1Channel(url=channel, used_env_vars=[])
            for channel in env.config.channels
        ]

        metadata = CondaLockV1Metadata(
            content_hash={},  # Empty for now, could be computed later
            channels=channels,
            platforms=sorted(e.platform for e in env_list),
            sources=[""],  # Empty source as before
            time_metadata=CondaLockV1TimeMetadata(created_at=timestamp),
            custom_metadata=CondaLockV1CustomMetadata(
                created_by=f"conda-lockfiles {__version__}"
            ),
        )

        # Construct and return CondaLockV1 instance
        return cls(version=1, metadata=metadata, package=packages)

    def as_conda_env(self, platform: str = context.subdir) -> Environment:
        """
        Render lockfile as a conda environment.

        :param platform: Platform to extract packages for
        :return: Conda Environment object
        """
        # Validate platform is available
        if platform not in self.metadata.platforms:
            raise ValueError(
                f"Platform {platform} not found in lockfile. "
                f"Available platforms: {', '.join(self.metadata.platforms)}"
            )

        config = EnvironmentConfig(
            channels=tuple(
                Channel(channel.url).canonical_name
                for channel in self.metadata.channels
            ),
        )

        explicit_packages: dict[str, dict[str, Any]] = {}
        external_packages: dict[str, list[str]] = {}

        for pkg in self.package:
            # Filter packages
            if pkg.platform != platform:
                continue
            if pkg.category != "main":
                continue
            if pkg.optional:
                continue
            if not pkg.url:
                continue

            # Group by manager
            if pkg.manager == "conda":
                explicit_packages[pkg.url] = _package_to_record_overrides(pkg)
            else:
                try:
                    key = PACKAGE_TYPES[pkg.manager]
                except KeyError:
                    raise ValueError(f"Unknown package type: {pkg.manager}")
                external_packages.setdefault(key, []).append(pkg.url)

        return Environment(
            prefix=context.target_prefix,
            platform=platform,
            config=config,
            explicit_packages=records_from_conda_urls(explicit_packages),
            external_packages=external_packages,
        )


def _record_to_package(
    record: PackageRecord,
    platform: str,
) -> CondaLockV1Package:
    """
    Convert a conda PackageRecord to a CondaLockV1Package Pydantic model.

    :param record: Conda package record
    :param platform: Platform string for this package
    :return: CondaLockV1Package with metadata
    """
    # Convert dependencies from list to dict
    dependencies = {}
    for dep in record.depends:
        ms = MatchSpec(dep)
        version = ms.version.spec_str if ms.version is not None else ""
        dependencies[ms.name] = version

    # Build hash dict
    hash_dict = CondaLockV1Hash(
        md5=record.md5 if record.md5 else None,
        sha256=record.sha256 if record.sha256 else None,
    )

    return CondaLockV1Package(
        name=record.name,
        version=record.version,
        manager="conda",
        platform=platform,
        dependencies=dependencies,
        url=record.url,
        hash=hash_dict,
        category="main",
        optional=False,
    )


def _package_to_record_overrides(pkg: CondaLockV1Package) -> dict[str, Any]:
    """
    Convert CondaLockV1Package to record overrides dict.

    :param pkg: Package from lockfile
    :return: Dict of overrides for records_from_conda_urls
    """
    if pkg.manager != "conda":
        raise ValueError(f"Unsupported manager: {pkg.manager}")

    return {
        # dependencies are converted to a list of strings
        "depends": [f"{name} {version}" for name, version in pkg.dependencies.items()],
        # platform is renamed to subdir
        "subdir": pkg.platform,
        # pass through other fields
        "name": pkg.name,
        "version": pkg.version,
        "hash": pkg.hash.model_dump(exclude_none=True),
    }


def multiplatform_export(envs: Iterable[Environment]) -> str:
    """Export Environment to conda-lock v1 format."""
    lockfile = CondaLockV1.from_conda_envs(envs)
    try:
        # Exclude None values from serialization
        return yaml_safe_dump(lockfile.model_dump(exclude_none=True, mode="python"))
    except YAMLError as e:
        raise CondaValueError(
            f"Failed to export environment to conda-lock v1 format: {e}"
        ) from e


class CondaLockV1Loader(EnvironmentSpecBase):
    detection_supported: ClassVar[bool] = True

    def __init__(self, path: PathType):
        self.path = Path(path).resolve()
        self._model: CondaLockV1 | None = None

    def can_handle(self) -> bool:
        """
        Attempts to validate loaded data as a conda lock v1 specification.

        :raises ValueError: Raised when validation fails
        """
        # Check filename first
        if self.path.name not in DEFAULT_FILENAMES:
            raise ValueError(
                f"Invalid filename: {self.path}; please choose one from: "
                f"{DEFAULT_FILENAMES}"
            )

        try:
            return self._validate_model()
        except (FileNotFoundError, YAMLError) as e:
            raise ValueError(f"Cannot load file {self.path}: {e}") from e

    def _validate_model(self) -> bool:
        """
        Attempt to load model.

        :returns: indicates successful load
        :raises ValueError: raised when validation fails
        """
        try:
            self._model = CondaLockV1.model_validate(self._data)
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
