import pytest
from conda.plugins import reporter_backends
from conda.plugins.hookspec import CondaSpecs
from conda.plugins.manager import CondaPluginManager

import conda_lockfiles.plugin

pytest_plugins = ("conda.testing.fixtures",)


@pytest.fixture
def plugin_manager() -> CondaPluginManager:
    manager = CondaPluginManager()
    manager.add_hookspecs(CondaSpecs)
    # since we invoke progress bars we need the reporter backends
    manager.load_plugins(*reporter_backends.plugins)
    manager.load_plugins(conda_lockfiles.plugin)
    return manager
