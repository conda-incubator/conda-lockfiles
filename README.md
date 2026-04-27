# conda-lockfiles

Support for different lockfiles in the `conda` CLI tool.

> [!IMPORTANT]
> This project is still in early stages of development. Don't use it in production (yet).
> We do welcome feedback on what the expected behaviour should have been if something doesn't work!

<!-- docs-index-content-start -->
## What is this?

conda-lockfiles adds support for additional lockfile formats to conda. It supports different types of lockfiles
from the ecosystem like [conda-lock](https://github.com/conda/conda-lock) or [pixi](https://github.com/prefix-dev/pixi).

The basic usage is:

```bash
# Create environment from lockfile
conda env create -n ENV-NAME --env-spec=FORMAT --file=/path/to/lockfile

# Export current environment to lockfile
conda export -n ENV-NAME --format=FORMAT --file=/path/to/lockfile
```

Use **`--format`** with **`conda export`** (output format) and **`--env-spec`** with **`conda env create`** when you must name the input format; **`--env-spec`** is optional if conda recognizes the filename.

Currently supported lockfile formats:

- `conda-lock.yml` / `conda-lock.yaml` — `conda-lock-v1` (alias: `conda-lock`)
- `pixi.lock` — `rattler-lock-v6` (aliases: `pixi`, `pixi-lock-v6`)

The version-pinned names (`-v1`, `-v6`) never change meaning. The short
aliases track the current-stable version. See [format
aliases](https://conda-incubator.github.io/conda-lockfiles/format-aliases.html)
for when to use which.

## Installation

This is a `conda` plugin and must be installed in the `base` environment:

```bash
conda install -n base conda-forge::conda-lockfiles
```

## Usage

### Creating a lockfile for the current environment

```bash
conda export --format=FORMAT --file=FILE
```

To specify additional platforms:

```bash
conda export --format=FORMAT --file=FILE [--override-platforms] --platform=PLATFORM ...
```

See [`conda export` docs](https://docs.conda.io/projects/conda/en/stable/commands/export.html) for more details.

### Creating a new environment from a lockfile

```bash
conda env create --file=FILE
```

If conda is unable to determine the file format:

```bash
conda env create --file=FILE --env-spec=FORMAT
```

See [`conda env create` docs](https://docs.conda.io/projects/conda/en/stable/commands/env/create.html) for more details.

### Examples

**Export one `conda-lock` file with several platforms** (adjust platforms to what you need; exporting a platform different than the host may fail):

```bash
conda export \
  --name myenv \
  --format conda-lock-v1 \
  --file conda-lock.yml \
  --platform linux-64 \
  --platform osx-64
```

**Create an environment from that lockfile**:

```bash
conda env create --name myenv --file conda-lock.yml
# if the format is not auto-detected:
conda env create --name myenv --file dev-lock.yml --env-spec=conda-lock-v1
```

**Pixi / rattler lock v6**:

```bash
conda export --name myenv --format pixi --file pixi.lock
conda env create --name myenv --file pixi.lock --env-spec=pixi
```

`pixi` resolves to `rattler-lock-v6` today. Use `--format
rattler-lock-v6` / `--env-spec=rattler-lock-v6` in committed lockfiles
and CI so a future alias flip doesn't change the written format.
<!-- docs-index-content-end -->

More information and example workflows are available on our online [documentation](https://conda-incubator.github.io/conda-lockfiles/).

## Contributing

Please refer to [`CONTRIBUTING.md`](/CONTRIBUTING.md).
