from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from conda.base.context import context
from conda.common.path import expand
from conda.common.url import is_url, join_url, path_to_url
from conda.exceptions import ParseError
from conda.models.match_spec import MatchSpec

from ..constants import EXPLICIT_KEY, HASH_KEYS
from .base import BaseLoader, subdict

if TYPE_CHECKING:
    from typing import Final

    from conda.common.path import PathType

    from ..types import CondaSpecsTuple, PypiRecords


URL_PAT: Final = re.compile(
    r"(?:(?P<url_p>.+)(?:[/\\]))?"
    r"(?P<fn>[^/\\#]+(?:\.tar\.bz2|\.conda))"
    r"(?:#("
    r"(?P<md5>[0-9a-f]{32})"
    r"|((sha256:)?(?P<sha256>[0-9a-f]{64}))"
    r"))?$"
)


class ExplicitLoader(BaseLoader):
    @classmethod
    def supports(cls, path: PathType) -> bool:
        path = Path(path)
        if not path.exists():
            return False
        data = cls._load(path)
        if EXPLICIT_KEY not in data:
            return False
        return True

    @staticmethod
    def _load(path: PathType) -> list[str]:
        return Path(path).read_text().splitlines()

    def to_conda_and_pypi(
        self,
        environment: str | None = None,  # unused
        platform: str = context.subdir,  # unused
    ) -> tuple[CondaSpecsTuple, PypiRecords]:
        conda = []
        for line in self.data:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line == EXPLICIT_KEY:
                continue

            spec = self._parse_package(line)
            conda.append(spec)

        return tuple(conda), ()

    @staticmethod
    def _parse_package(line: str) -> MatchSpec:
        # adapted from conda.misc::_match_specs_from_explicit
        if not is_url(line):
            line = path_to_url(expand(line))

        # parse URL
        match = URL_PAT.match(line)
        if match is None:
            raise ParseError(f"Could not parse explicit URL: {line}")

        # url_p is everything but the tarball_basename and the checksum
        url_p, fn = match.group("url_p"), match.group("fn")
        url = join_url(url_p, fn)

        hashes = subdict(match.groupdict(), HASH_KEYS)
        return MatchSpec(url, **hashes)
