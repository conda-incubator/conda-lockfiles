from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from conda.base.constants import KNOWN_SUBDIRS
from conda.base.context import context
from conda.models.records import PackageRecord
from conda.plugins.types import EnvironmentSpecBase

from ..constants import PIXI_LOCK_FILE
from .base import build_number_from_build_string, load_yaml

if TYPE_CHECKING:
    from conda.common.path import PathType
    from conda.models.environment import Environment


def _pixi_lock_to_env():
    pass


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
        return _pixi_lock_to_env(**load_yaml(self.path))

    def to_conda_and_pypi(
        self,
        environment: str = "default",
        platform: str = context.subdir,
    ) -> tuple[tuple[PackageRecord, ...], tuple[str, ...]]:
        env = self.data["environments"].get(environment)
        if not env:
            raise ValueError(
                f"Environment {environment} not found. "
                f"Available environment names: {sorted(self.data['environments'])}."
            )
        packages = env["packages"].get(platform)
        if not packages:
            raise ValueError(
                f"Environment {environment} does not list packages for platform "
                f"{platform}. Available platforms: {sorted(env['packages'])}."
            )

        conda, pypi = [], []
        for package in packages:
            for package_type, url in package.items():
                if package_type == "conda":
                    conda.append(self._package_record_from_conda_url(url))
                elif package_type == "pypi":
                    pypi.append(url)

        return tuple(conda), tuple(pypi)

    def _package_record_from_conda_url(self, url: str) -> PackageRecord:
        channel, subdir, filename = url.rsplit("/", 2)
        assert subdir in KNOWN_SUBDIRS, f"Unknown subdir '{subdir}' in package {url}."
        if filename.endswith(".tar.bz2"):
            basename = filename[: -len(".tar.bz2")]
            ext = ".tar.bz2"
        elif filename.endswith(".conda"):
            basename = filename[: -len(".conda")]
            ext = ".conda"
        else:
            basename, ext = os.path.splitext(filename)
        assert ext.lower() in (
            ".conda",
            ".tar.bz2",
        ), f"Unknown extension '{ext}' in package {url}."
        name, version, build = basename.rsplit("-", 2)
        build_number = build_number_from_build_string(build)
        record_fields = {
            "name": name,
            "version": version,
            "build": build,
            "build_number": build_number,
            "subdir": subdir,
            "channel": channel,
            "fn": filename,
        }
        for record in self.data["packages"]:
            if record.get("conda", "") == url:
                record_fields.update(record)
                record_fields["url"] = record_fields.pop("conda", None)
                break
        return PackageRecord(**record_fields)
