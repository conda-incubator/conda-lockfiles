# Format names and aliases

Each lockfile format has a version-pinned canonical name and, when a
short form reads better at the command line, an unversioned alias.

## Names today

| Canonical name    | Unversioned alias | Files                                |
| ----------------- | ----------------- | ------------------------------------ |
| `conda-lock-v1`   | `conda-lock`      | `conda-lock.yml`, `conda-lock.yaml`  |
| `rattler-lock-v6` | `pixi`            | `pixi.lock`                          |

`rattler-lock-v6` also accepts `pixi-lock-v6` for compatibility with
docs and tooling that use the `pixi-lock-v*` naming.

## What the two names mean

The canonical names (`conda-lock-v1`, `rattler-lock-v6`) identify one
specific file-format version and never change meaning. `conda-lock-v1`
will still be `conda-lock-v1` after `conda-lock-v2` ships. Use these in
committed lockfiles, CI pins, and anywhere a file is exchanged with
another tool.

The unversioned aliases (`conda-lock`, `pixi`) resolve to whichever
version is current-stable in the installed conda-lockfiles release. Use
these when you want the latest format and do not need the invocation to
outlive the next release.

Concretely: `conda export --format pixi` writes `rattler-lock-v6` today.
If a later release makes `rattler-lock-v7` current-stable, the same
command writes v7.

## Bump policy

When a new version of a format reaches stable, the alias is rolled over
two releases so the flip is never silent:

1. The new canonical name (`rattler-lock-v7`) ships alongside the old
   one. The unversioned alias (`pixi`) still points at the old version.
   Alias resolution emits a `PendingDeprecationWarning` naming the
   release in which the flip lands.
2. The next release flips the alias to the new canonical name. The old
   canonical name keeps working without warnings.
3. At a later release the old canonical name enters the standard
   `conda.deprecations.DeprecationHandler` cycle with a removal target.

Canonical names only participate in step 3.

### Maintainer checklist

When shipping a new format version:

- Register it under its canonical name in `conda_lockfiles/plugin.py`.
- Leave the unversioned alias pointing at the previous canonical name.
- Emit a `PendingDeprecationWarning` on alias resolution naming the
  flip release.
- Add tests covering both canonical names and confirming the alias
  still resolves to the previous format.
- Update the "Names today" table.

When flipping the alias:

- Point the unversioned alias at the new canonical name.
- Drop the `PendingDeprecationWarning`; call out the flip in the
  release notes.
- Update the "Names today" table.

When retiring the old version:

- Mark the old canonical name with `conda.deprecations.deprecated` and
  a removal target.
- Update the "Names today" table.

## Re-exporting a lockfile at a new format version

Existing `pixi.lock` files on disk remain valid after an alias flip;
nothing rewrites them. To upgrade one, re-create the environment from
the existing file and re-export at the new format:

```shell
conda env create --name lockfile-upgrade --file pixi.lock
conda export \
  --name lockfile-upgrade \
  --format rattler-lock-v7 \
  --file pixi.lock \
  --platform linux-64 \
  --platform osx-arm64 \
  --platform win-64
```

Pin the new canonical name in the re-export so the command is
unaffected by future alias flips. The same pattern works for
`conda-lock-v1` → a future `conda-lock-v2`.
