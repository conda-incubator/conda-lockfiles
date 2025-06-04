from typing import Any

from conda.base.context import context
from conda.core.package_cache_data import PackageCacheData, ProgressiveFetchExtract
from conda.exceptions import (
    CondaExitZero,
    DryRunExit,
)
from conda.models.match_spec import MatchSpec
from conda.models.records import PackageRecord

CondaPackageURL = str
CondaPackageMetadata = dict[str, Any]


def records_from_urls_and_metadata(
    metadata_by_url: dict[CondaPackageURL, CondaPackageMetadata],
    dry_run: bool = context.dry_run,
    download_only: bool = context.download_only,
) -> tuple[PackageRecord, ...]:
    fetch_specs = [
        MatchSpec(
            url, **{key: metadata[key] for key in ("md5", "sha256") if key in metadata}
        )
        for url, metadata in metadata_by_url.items()
    ]
    if dry_run:
        raise DryRunExit()

    pfe = ProgressiveFetchExtract(fetch_specs)
    pfe.execute()

    if download_only:
        raise CondaExitZero(
            "Package caches prepared. Installed cancelled with --download-only option."
        )

    records: list[PackageRecord] = []
    for fetch_spec in fetch_specs:
        cache_record = next(PackageCacheData.query_all(fetch_spec), None)
        if cache_record is None:
            raise AssertionError(f"Missing package cache record for: {fetch_spec}")
        url = fetch_spec.get("url")
        overrides = metadata_by_url.get(url, {})
        records.append(
            PackageRecord.from_objects(
                cache_record,
                **overrides,
            )
        )
    return records
