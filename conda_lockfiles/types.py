from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import NotRequired, TypedDict

    from conda.models.match_spec import MatchSpec
    from conda.models.records import PackageRecord

    class CondaRecordOverrides(TypedDict):
        """Fields to override when creating a PackageRecord from a PackageCacheRecord.

        Attributes:
            depends: List of package dependencies.
            constrains: List of package constrains.
        """

        depends: NotRequired[list[str]]
        constrains: NotRequired[list[str]]

    CondaSpecsTuple = tuple[MatchSpec, ...]
    CondaSpecsMapping = Mapping[MatchSpec, CondaRecordOverrides]
    CondaSpecs = CondaSpecsTuple | CondaSpecsMapping
    CondaRecords = tuple[PackageRecord, ...]

    PypiRecords = tuple[str, ...]
