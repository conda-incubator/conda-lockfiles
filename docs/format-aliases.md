# Format names and aliases

`conda-lockfiles` exposes each lockfile format under a version-pinned
canonical name and, where it makes sense, a shorter unversioned alias.
The two serve different purposes: canonical names are a stable contract,
aliases are convenience. This document describes which is which today,
how the alias tracks future format versions, and how to migrate an
existing lockfile when the alias flips.

## Format names today

| Canonical name   | Unversioned alias | Description                                       |
| ---------------- | ----------------- | ------------------------------------------------- |
| `conda-lock-v1`  | `conda-lock`      | Multi-platform `conda-lock.yml` / `.yaml` files.  |
| `rattler-lock-v6`| `pixi`            | `pixi.lock` files produced by the rattler engine. |

`rattler-lock-v6` additionally carries `pixi-lock-v6` as a second
version-pinned alias for backwards compatibility with docs and tooling
that reference the `pixi-lock-v*` naming.

## Canonical vs. unversioned: what the two promise

- **Canonical names (`conda-lock-v1`, `rattler-lock-v6`)** are the stable
  contract. They identify one specific file-format version and are
  guaranteed not to move under you: `conda-lock-v1` will always mean the v1
  spec, even after `conda-lock-v2` ships. Pin these when you care about
  reproducibility or interoperability with external tooling.
- **Unversioned aliases (`conda-lock`, `pixi`)** are convenience. They
  track whatever version is current-stable in the conda-lockfiles release
  you have installed. Use these in day-to-day commands and docs where the
  latest stable format is what you want.

If you have a `pixi.lock` file and type `conda export --format pixi`, the
current release writes `rattler-lock-v6`. After a future release flips the
alias to, say, `rattler-lock-v7`, the same command writes v7 instead. The
tutorial below walks through re-exporting an existing file at a new format
version.

## Alias bump policy

When the current-stable format version changes (e.g. `rattler-lock-v6`
→ `rattler-lock-v7`), conda-lockfiles rolls the unversioned alias over a
two-release window so that users who type the short form are warned before
the output changes:

1. **Release _N_ — new version ships pinned.** The new format is added
   under its canonical name (e.g. `rattler-lock-v7`). The unversioned alias
   (`pixi`) still resolves to the previous version (`rattler-lock-v6`). A
   `PendingDeprecationWarning` is emitted on the alias resolution path
   noting the release in which the flip is planned.
2. **Release _N+1_ — alias flip.** The unversioned alias is re-pointed to
   the new canonical version. Users who type the pinned old name
   (`rattler-lock-v6`) keep getting the old format without warnings. Users
   who type the pinned new name (`rattler-lock-v7`) or the unversioned
   alias (`pixi`) get the new format.
3. **Release _N+K_ — deprecation and removal.** When usage of the old
   pinned name has dropped off, it enters conda's standard deprecation
   cycle (`conda.deprecations.DeprecationHandler`) with a clearly stated
   removal target release.

Canonical names only participate in step 3. They never silently change
meaning.

### Maintainer checklist for a version bump

Pre-bump:

- [ ] Add the new format module under its canonical name and register it
      in `conda_lockfiles/plugin.py` alongside the existing one.
- [ ] Keep the existing unversioned alias pointing at the previous
      canonical name.
- [ ] Wire a `PendingDeprecationWarning` on unversioned-alias resolution
      that names the upcoming flip release.
- [ ] Add tests that (a) both canonical names resolve, and (b) the
      unversioned alias still resolves to the previous format.
- [ ] Update this document's "Format names today" table with a row for the
      new canonical name, and add a note that the unversioned alias flip
      is scheduled for release _N+1_.

Bump release:

- [ ] Move the unversioned alias to the new canonical format.
- [ ] Swap the `PendingDeprecationWarning` for a release-note entry
      describing the flip.
- [ ] Update this document: the unversioned alias now tracks the new
      version; the previous version stays supported under its pinned name.

Deprecation release:

- [ ] Mark the old canonical name via `conda.deprecations.deprecated` with
      a concrete removal target.
- [ ] Update this document to list the name as deprecated.

## Tutorial: re-exporting an existing lockfile at a new format version

If a future release flips `pixi` from `rattler-lock-v6` to
`rattler-lock-v7`, an existing `pixi.lock` on disk is still valid — nothing
rewrites files on your behalf. To move it to the new format, re-export
from an environment that matches the lockfile.

Re-create the environment from the existing file:

```shell
conda env create --name lockfile-upgrade --file pixi.lock
```

Export it at the new format. Pin the new version explicitly so the command
keeps doing the same thing regardless of future alias flips:

```shell
conda export \
  --name lockfile-upgrade \
  --format rattler-lock-v7 \
  --file pixi.lock \
  --platform linux-64 \
  --platform osx-arm64 \
  --platform win-64
```

The same pattern applies to `conda-lock-v1` → `conda-lock-v2` once that
version exists; substitute the canonical names accordingly.

If you want the short form during an alias-flip window:

```shell
conda export --name lockfile-upgrade --format pixi --file pixi.lock ...
```

This writes whatever the current release of conda-lockfiles treats as
`pixi`-stable. The current mapping is recorded in the "Format names today"
table above.

## Picking the right name for your situation

- **Committing lockfiles to a repo or pinning in CI.** Use the canonical
  name (`conda-lock-v1`, `rattler-lock-v6`). The invocation is stable
  across conda-lockfiles releases.
- **Ad-hoc commands, docs, READMEs.** Use the unversioned alias
  (`conda-lock`, `pixi`). The short form is what most users recognise and
  it keeps tracking the current-stable format.
- **Tooling that exchanges files with `conda-lock` or `pixi` directly.**
  Use the canonical name matching the file-format version the other tool
  understands.
