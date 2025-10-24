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

Currently supported lockfile formats:

- conda-lock.yml (`conda-lock-v1`)
- pixi.lock (`rattler-lock-v6` or `pixi-lock-v6`)

## Installation

This is a `conda` plugin and must be installed in the `base` environment:

```bash
conda install -n base conda-forge::conda-lockfiles
```

<!-- docs-index-content-end -->

More information is available on our [documentation](https://conda-incubator.github.io/conda-lockfiles/).

## Contributing

Please refer to [`CONTRIBUTING.md`](/CONTRIBUTING.md).
