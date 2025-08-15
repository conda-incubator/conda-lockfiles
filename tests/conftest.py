from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from conda.plugins import reporter_backends
from conda.plugins.hookspec import CondaSpecs
from conda.plugins.manager import CondaPluginManager

import conda_lockfiles.plugin

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

pytest_plugins = ("conda.testing.fixtures",)


@pytest.fixture
def plugin_manager(mocker: MockerFixture) -> CondaPluginManager:
    manager = CondaPluginManager()
    manager.add_hookspecs(CondaSpecs)
    mocker.patch("conda.plugins.manager.get_plugin_manager", return_value=manager)
    # since we invoke progress bars we need the reporter backends
    manager.load_plugins(*reporter_backends.plugins)
    manager.load_plugins(conda_lockfiles.plugin)
    return manager
