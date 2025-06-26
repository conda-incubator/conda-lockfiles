from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from conda.base.context import context

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from typing import Any

    from conda.common.path import PathType

    from ..types import CondaSpecs, PypiRecords


class BaseLoader(ABC):
    def __init__(self, path: PathType):
        self.path = Path(path)
        self.data = self._load(path)

    @classmethod
    @abstractmethod
    def supports(cls, path: PathType) -> bool:
        raise NotImplementedError

    @abstractmethod
    def _load(self, path: PathType) -> Any:
        raise NotImplementedError

    @abstractmethod
    def to_conda_and_pypi(
        self,
        environment: str | None = None,
        platform: str = context.subdir,
    ) -> tuple[CondaSpecs, PypiRecords]:
        raise NotImplementedError


# FUTURE: Python 3.12+ use generic function syntax
# def subdict[T: str](mappping: Mapping[str, Any], keys: Iterable[T]) -> dict[T, Any]:
def subdict(mapping: Mapping[str, Any], keys: Iterable[str]) -> dict[str, Any]:
    return {key: mapping[key] for key in keys if key in mapping}
