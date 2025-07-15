""" """

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.exceptions import CondaError

if TYPE_CHECKING:
    from pathlib import Path

    from conda.common.path import PathType
    from conda.models.match_spec import MatchSpec


class LockfileFormatNotSupported(CondaError):
    def __init__(self, path: PathType | Path):
        message = f"The specified file {path} is not supported."
        super().__init__(message)


class ExportLockfileFormatNotSupported(CondaError):
    def __init__(self, lockfile_format: str):
        message = f"Exporting to lockfile format {lockfile_format} is not supported."
        super().__init__(message)


class MissingPackageCacheRecord(CondaError):
    def __init__(self, match_spec: MatchSpec):
        message = f"Missing package cache record for: {match_spec}"
        super().__init__(message)


class MultiplePackageCacheRecords(CondaError):
    def __init__(self, match_spec: MatchSpec):
        message = f"Multiple package cache records for: {match_spec}"
        super().__init__(message)


class InvalidCondaRecordOverrides(CondaError):
    def __init__(self, match_spec: MatchSpec, invalid_overrides: set[str]):
        keys = ", ".join(sorted(invalid_overrides))
        message = f"Invalid overrides for {match_spec}: {keys}"
        super().__init__(message)
