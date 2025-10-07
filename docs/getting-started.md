# Getting Started

The `conda-lockfiles` plugin is integrated directly into the following conda commands:

- `conda env create`
- `conda export`

The `env create` and `export` commands allow you to create environments from lockfiles or
save and share them, respectively.

## Using `conda env create` to create environments from lockfiles

In this example, we show how to create an environment from a lockfile generated
with [pixi](https://github.com/prefix-dev/pixi):

```shell
conda env create --name my-env --format pixi-lock-v6  --file pixi.lock
```

:::{notice}
This needs to be a version 6 format of the pixi lock file. Earlier versions
may cause errors.
:::

## Using `conda export` to save lockfiles

This example shows how to export environment we created above (`my-env`) as a
lockfile using the `conda-lock-v1` format:

```shell
conda export --name my-env  --env-spec=conda-lock-v1 > conda-lock.yml
```

## Using `conda export` to save lockfiles with a different platform

If you have created an environment with the following command on the `linux-64` platform:

```shell
conda create --name python-env --yes python
```

it's possible to export it to a lockfile using the `win-64` platform with the following command:

```shell
conda export --name python-env --format pixi-lock-v6 --platform win-64 > pixi.lock
```

:::{warning}
Currently, it is not possible to create an environment from a lockfile and then export it using a 
different platform. For example, an environment created using a lockfile using the `linux-64` platform
cannot be exported to the `win-64` platform.
:::

## Tips on usage

- These lockfiles can be saved to your repositories and used in CI workflows
  for faster execution times
- They can also be used with `conda-lock` and `pixi`
- This project is still in beta; please file bugs and feature requests [here](https://github.com/conda-incubator/conda-lockfiles)