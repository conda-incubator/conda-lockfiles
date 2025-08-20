from __future__ import annotations

from typing import TYPE_CHECKING

from conda.base.context import context

if TYPE_CHECKING:
    from conda.plugins.manager import CondaPluginManager

from conda_lockfiles.conda_lock import v1 as conda_lock_v1
from conda_lockfiles.rattler_lock import v6 as rattler_lock_v6

from . import CONDA_LOCK_METADATA_DIR, PIXI_METADATA_DIR

CONDA_LOCK_METADATA_BUILDS = {
    "linux-64": "hee588c1_0",
    "osx-64": "hdb6dae5_0",
    "osx-arm64": "h3f77e49_0",
    "win-64": "h67fdade_0",
}

CONDA_LOCK_METADATA_SHA256 = {
    "linux-64": "b3dcd409c96121c011387bdf7f4b5758d876feeb9d8e3cfc32285b286931d0a7",
    "osx-64": "e88ea982455060b96fdab3d360b947389248bf2139e3b17576e4c72e139526fc",
    "osx-arm64": "80bbe9c53d4bf2e842eccdd089653d0659972deba7057cda3ebaebaf43198f79",
    "win-64": "92546e3ea213ee7b11385b22ea4e7c69bbde1c25586288765b37bc5e96b20dd9",
}

CONDA_LOCK_METADATA_MD5 = {
    "linux-64": "71888e92098d0f8c41b09a671ad289bc",
    "osx-64": "caf16742f7e16475603cd9981ef36195",
    "osx-arm64": "cda0ec640bc4698d0813a8fb459aee58",
    "win-64": "92b11b0b2120d563caa1629928122cee",
}


def test_create_environment_from_conda_lock_v1(
    plugin_manager: CondaPluginManager,
) -> None:
    path = CONDA_LOCK_METADATA_DIR / conda_lock_v1.CONDA_LOCK_FILE
    loader = plugin_manager.get_environment_specifier(
        path,
        conda_lock_v1.FORMAT,
    )
    assert loader.name == conda_lock_v1.FORMAT
    assert loader.environment_spec == conda_lock_v1.CondaLockV1Loader

    spec = loader.environment_spec(path)
    assert spec.can_handle()
    assert spec.env
    assert spec.env.prefix == context.target_prefix
    assert spec.env.platform == context.subdir
    assert not spec.env.requested_packages
    assert not spec.env.external_packages

    explicit_packages = spec.env.explicit_packages
    # each platform may have a different number of packages
    assert explicit_packages

    pkg = next(pkg for pkg in explicit_packages if pkg.name == "libsqlite")
    assert pkg.name == "libsqlite"
    assert pkg.version == "3.50.0"
    assert pkg.build == CONDA_LOCK_METADATA_BUILDS[context.subdir]
    assert pkg.sha256 == CONDA_LOCK_METADATA_SHA256[context.subdir]
    assert pkg.md5 == CONDA_LOCK_METADATA_MD5[context.subdir]
    assert pkg.depends == ("ONLY_IN_LOCKFILE 0",)


def test_create_environment_from_rattler_lock_v6(
    plugin_manager: CondaPluginManager,
) -> None:
    path = PIXI_METADATA_DIR / rattler_lock_v6.PIXI_LOCK_FILE
    loader = plugin_manager.get_environment_specifier(
        path,
        rattler_lock_v6.FORMAT,
    )
    assert loader.name == rattler_lock_v6.FORMAT
    assert loader.environment_spec == rattler_lock_v6.RattlerLockV6Loader

    spec = loader.environment_spec(path)
    assert spec.can_handle()
    assert spec.env
    assert spec.env.prefix == context.target_prefix
    assert spec.env.platform == context.subdir
    assert not spec.env.requested_packages
    assert not spec.env.external_packages

    explicit_packages = spec.env.explicit_packages
    assert len(explicit_packages) == 1

    pkg = explicit_packages[0]
    assert pkg.name == "tzdata"
    assert pkg.version == "2025b"
    assert pkg.build == "h78e105d_0"
    assert pkg.build_number == 0
    assert (
        pkg.sha256 == "5aaa366385d716557e365f0a4e9c3fca43ba196872abbbe3d56bb610d131e192"
    )
    assert pkg.md5 == "4222072737ccff51314b5ece9c7d6f5a"
    assert pkg.license == "ONLY_IN_LOCKFILE"
    assert pkg.size == 122968
    assert pkg.timestamp == 1742727099.393
