from __future__ import annotations

from conda_lockfiles.loaders.base import subdict


def test_subdict() -> None:
    mapping = {"a": 1, "b": 2, "c": 3}
    assert subdict(mapping, ["a"]) == {"a": 1}
    assert subdict(mapping, ["b"]) == {"b": 2}
    assert subdict(mapping, ["c"]) == {"c": 3}
    assert subdict(mapping, ["a", "b"]) == {"a": 1, "b": 2}
    assert subdict(mapping, ["a", "d"]) == {"a": 1}
