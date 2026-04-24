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

## Alias ordering convention

The `ALIASES` tuple in each format module puts the short unversioned
alias first. conda uses the first alias as the display label in
`--help` output, with the canonical name and any remaining aliases
shown in parentheses:

```
Lockfiles:
  - pixi (rattler-lock-v6, pixi-lock-v6)
  - conda-lock (conda-lock-v1)
```

All names in the tuple, and the canonical name itself, remain valid
everywhere conda accepts a `--format` value. The ordering only affects
the help label.

When adding a new alias, place the short form first.

## Default filenames across versions

Each format's `default_filenames` is the filename users are already
typing (`pixi.lock`, `conda-lock.yml`). A new version of the same
format claims the same filenames; conda-lockfiles does not invent
`pixi-v7.lock`.

That means two export plugins can register the same `default_filenames`
entry once a new version ships alongside the old one. `conda export
--file pixi.lock` (no `--format`) needs conda to pick one. Conda today
raises `PluginError` on that collision;
[conda/conda#15963](https://github.com/conda/conda/issues/15963) tracks
the tiebreaker work so conda picks the current-stable plugin. Until
that lands, users pass `--format rattler-lock-vN` alongside `--file
pixi.lock` during the overlap release.

On the read side, `conda env create -f pixi.lock` dispatches on file
contents. Each specifier's `can_handle()` rejects files it cannot
parse, so both plugins can coexist without manual disambiguation.

`--file pixi.lock` without `--format` writes current-stable (whatever
`pixi` currently resolves to) once the tiebreaker in conda/conda#15963
lands. Pin `--format rattler-lock-v6` when the format version needs to
outlive the next alias flip.

## Bump policy

When a new version of a format reaches stable, the alias is rolled
over two releases so the flip is never silent:

1. **Overlap release.** The new canonical name (`rattler-lock-v7`)
   ships alongside the old one (`rattler-lock-v6`). The unversioned
   alias (`pixi`) still resolves to the old canonical name. Alias
   resolution emits a `PendingDeprecationWarning` with wording that
   names the binding change, not a format deprecation:

   ```
   PendingDeprecationWarning: 'pixi' currently resolves to
   rattler-lock-v6 and will resolve to rattler-lock-v7 in
   conda-lockfiles <version>. Pin --format rattler-lock-v6 to keep
   writing v6 after the flip.
   ```

   Python's default filter silences `PendingDeprecationWarning` for
   end users and shows it in tests and `python -W` runs, which is the
   right volume for "this alias is about to flip, it may matter to
   you".

2. **Flip release.** The unversioned alias now resolves to the new
   canonical name. First alias resolution per process emits a one-shot
   `DeprecationWarning`:

   ```
   DeprecationWarning: 'pixi' now resolves to rattler-lock-v7 (was
   rattler-lock-v6 in the previous release). Pin --format
   rattler-lock-v6 if you need the old format.
   ```

   `DeprecationWarning` (not `PendingDeprecationWarning`) because the
   change has landed and Python's default filter shows it once per
   location per process, so anyone who did not read the release notes
   sees the flip exactly once. The old canonical name keeps working;
   no warning on it.

3. **Removal release.** The old canonical name (`rattler-lock-v6`)
   enters the standard `conda.deprecations.deprecated` cycle with a
   concrete `remove_in` target. The one-shot `DeprecationWarning` from
   step 2 is dropped; the binding is stable again.

Canonical names only participate in step 3. The unversioned alias
(`pixi`, `conda-lock`) itself is never removed.

The implementation of the warnings in steps 1 and 2 is tracked in
[#133](https://github.com/conda-incubator/conda-lockfiles/issues/133)
and will land alongside the first real format bump.

### Maintainer checklist

When shipping a new format version (overlap release):

- Register it under its canonical name in `conda_lockfiles/plugin.py`.
- Set `default_filenames` to match the previous canonical version
  (`pixi.lock` stays `pixi.lock`).
- Leave the unversioned alias pointing at the previous canonical name.
- When alias resolution picks the unversioned alias, raise
  `PendingDeprecationWarning` with wording that names the binding
  change (not a format deprecation) and names the flip release.
- Announce the upcoming flip in the release notes.
- Add tests covering both canonical names and confirming the alias
  still resolves to the previous format.
- Update the "Names today" table.

When flipping the alias (flip release):

- Point the unversioned alias at the new canonical name.
- On first alias resolution per process, raise a one-shot
  `DeprecationWarning` naming the flip that just happened and pointing
  at the pin command.
- Call out the flip in the release notes.
- Update the "Names today" table.

When retiring the old version (removal release):

- Mark the old canonical name with `conda.deprecations.deprecated` and
  a removal target.
- Drop the one-shot `DeprecationWarning` from step 2.
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
`conda-lock-v1` to a future `conda-lock-v2`.
