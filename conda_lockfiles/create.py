from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from subprocess import run
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING

from conda.base.context import context
from conda.common.compat import on_win
from conda.core.link import PrefixSetup, UnlinkLinkTransaction
from conda.core.package_cache_data import PackageCacheData, ProgressiveFetchExtract
from conda.core.prefix_data import PrefixData
from conda.exceptions import CondaExitZero, DryRunExit
from conda.models.prefix_graph import PrefixGraph
from conda.models.records import PackageRecord

from .constants import OVERRIDE_KEYS
from .exceptions import (
    InvalidCondaRecordOverrides,
    LockfileFormatNotSupported,
    MissingPackageCacheRecord,
    MultiplePackageCacheRecords,
)
from .loaders import LOADERS

if TYPE_CHECKING:
    from pathlib import Path
    from subprocess import CompletedProcess

    from conda.common.path import PathType

    from .types import CondaRecords, CondaSpecs, PypiRecords


def create_environment_from_lockfile(
    lockfile: PathType | Path,
    prefix: PathType | Path,
    environment: str | None = None,
    platform: str = context.subdir,
    dry_run: bool = False,
    download_only: bool = False,
    verbose: bool = False,
) -> None:
    for Loader in LOADERS:
        if Loader.supports(lockfile):
            break
    else:
        raise LockfileFormatNotSupported(lockfile)

    loader = Loader(lockfile)
    conda_specs, pypi_records = loader.to_conda_and_pypi(environment, platform)

    if dry_run:
        raise DryRunExit()

    if conda_specs:
        if verbose:
            print("Installing Conda packages:")
        conda_records = lookup_conda_records(conda_specs)

        if download_only:
            raise CondaExitZero(
                "Package caches prepared. Installation cancelled with --download-only."
            )

        install_conda_records(conda_records, prefix, verbose)

    if pypi_records:
        if verbose:
            print("Installing PyPI packages:")
        install_pypi_records(pypi_records, prefix)


def install_pypi_records(
    pypi_records: PypiRecords,
    prefix: PathType | Path,
) -> CompletedProcess:
    with NamedTemporaryFile("w", delete=False) as f:
        f.write("\n".join(pypi_records))

    if on_win:
        python_exe = os.path.join(prefix, "python.exe")
    else:
        python_exe = os.path.join(prefix, "bin", "python")
    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--prefix",
        prefix,
        "-r",
        f.name,
        "--no-deps",
        "--python",
        python_exe,
    ]
    try:
        return run(command, check=True)
    finally:
        os.unlink(f.name)


def lookup_conda_records(conda_specs: CondaSpecs) -> CondaRecords:
    # normalize specs to a mapping of MatchSpec -> CondaRecordOverrides
    if not isinstance(conda_specs, Mapping):
        conda_specs = {spec: {} for spec in conda_specs}
    conda_specs = dict(conda_specs)

    # populate package cache
    pfe = ProgressiveFetchExtract(conda_specs.keys())
    pfe.execute()

    # lookup records in package cache
    conda_records: list[PackageRecord] = []
    for match_spec, overrides in conda_specs.items():
        cache_records = tuple(PackageCacheData.query_all(match_spec))
        if not cache_records:
            raise MissingPackageCacheRecord(match_spec)
        elif len(cache_records) > 1:
            raise MultiplePackageCacheRecords(match_spec)
        elif invalid_overrides := set(overrides) - OVERRIDE_KEYS:
            # limit what keys from repodata.json are allowed to be overridden
            # do not want to allow overriding things like license, etc.
            raise InvalidCondaRecordOverrides(match_spec, invalid_overrides)
        conda_records.append(PackageRecord.from_objects(cache_records[0], **overrides))
    return tuple(conda_records)


def install_conda_records(
    conda_records: CondaRecords,
    prefix: PathType | Path,
    verbose: bool = False,
) -> None:
    # determine which packages need to be linked and unlinked
    unlink_precs: list[PackageRecord] = []
    link_precs: list[PackageRecord] = []
    prefix_data = PrefixData(prefix)
    for record in PrefixGraph(conda_records).graph:
        installed_record = prefix_data.get(record.name, None)
        if installed_record:
            # If the record is already installed, do not re-linking it
            if installed_record != record:
                unlink_precs.append(installed_record)
                link_precs.append(record)
        else:
            link_precs.append(record)

    # create and execute transaction
    stp = PrefixSetup(
        target_prefix=str(prefix),
        unlink_precs=tuple(unlink_precs),
        link_precs=tuple(link_precs),
        remove_specs=(),
        update_specs=(),
        neutered_specs=(),
    )
    txn = UnlinkLinkTransaction(stp)
    if verbose:
        txn.print_transaction_summary()
    txn.execute()
