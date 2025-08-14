# conda-lockfiles

Support for different lockfiles in the `conda` CLI tool.

> [!IMPORTANT]
> This project is still in early stages of development. Don't use it in production (yet).
> We do welcome feedback on what the expected behaviour should have been if something doesn't work!

## What is this?

conda-lockfiles adds support for additioanl lockfile formats to conda. It supports different types of lockfiles in the ecosystem.

The basic usage is:

```bash
# Create environment from lockfile
conda env create -n ENV-NAME PATH-TO.LOCKFILE
# Export current environment to lockfile
conda export -n ENV-NAME --format FORMAT
```

Currently supported lockfile formats:

- conda-lock.yml (conda-lock v1)
- pixi.lock (rattler_lock v6)

## Installation

This is a `conda` plugin and goes in the `base` environment:

```bash
conda install -n base conda-forge::conda-lockfiles  # Not available yet
```

More information is available on our [documentation](https://conda-incubator.github.io/conda-lockfiles/).

## Contributing

Please refer to [`CONTRIBUTING.md`](/CONTRIBUTING.md).
