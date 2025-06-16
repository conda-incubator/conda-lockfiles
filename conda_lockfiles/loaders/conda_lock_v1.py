from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from conda.base.context import context
from conda.models.match_spec import MatchSpec
from ruamel.yaml import YAML

from ..constants import CONDA_LOCK_FILE
from .base import BaseLoader, subdict

if TYPE_CHECKING:
    from typing import Any, Final

    from conda.common.path import PathType

    from ..types import CondaRecordOverrides, CondaSpecsMapping, PypiRecords

yaml: Final = YAML(typ="safe")


class CondaLockV1Loader(BaseLoader):
    @classmethod
    def supports(cls, path: PathType) -> bool:
        path = Path(path)
        if path.name != CONDA_LOCK_FILE or not path.exists():
            return False
        data = cls._load(path)
        if data["version"] != 1:
            return False
        return True

    @staticmethod
    def _load(path: PathType) -> dict[str, Any]:
        with open(path) as f:
            return yaml.load(f)

    def to_conda_and_pypi(
        self,
        environment: str | None = None,  # unused
        platform: str = context.subdir,
    ) -> tuple[CondaSpecsMapping, PypiRecords]:
        platforms = self.data.get("metadata", {}).get("platforms")
        if platform not in platforms:
            raise ValueError(
                f"Lockfile does not list packages for platform {platform}. "
                f"Available platforms: {', '.join(sorted(platforms))}."
            )

        conda = {}
        pypi = []
        for package in self.data["package"]:
            if package.get("platform") != platform:
                continue
            if package.get("category") != "main":
                continue
            if package.get("optional"):
                continue

            package_type = package.get("manager")
            if package_type == "conda":
                spec, overrides = self._parse_package(package)
                conda[spec] = overrides
            elif package_type == "pip":
                pypi.append(package["url"])
            else:
                raise ValueError(f"Unknown package type: {package_type}")

        return conda, tuple(pypi)

    @staticmethod
    def _parse_package(
        package: dict[str, Any],
    ) -> tuple[MatchSpec, CondaRecordOverrides]:
        url = package["url"]
        hashes = subdict(package.get("hash", {}), ["md5", "sha256"])
        overrides: CondaRecordOverrides = {
            # conda-lock v1 stores dependencies as a mapping of package name -> spec,
            # convert to a list of match spec strings
            "depends": [
                f"{name} {spec}"
                for name, spec in package.get("dependencies", {}).items()
            ]
        }
        return MatchSpec(url, **hashes), overrides
