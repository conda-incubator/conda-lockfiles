# Motivation

`conda-lockfiles` is a plugin that enables lockfile support in conda.
To do this, we are standing on the shoulders of one very important project that
came before it: [conda-lock](https://github.com/conda/conda-lock).
This project is different from `conda-lock` in the following ways:

1. Support for more than just the `conda-lock` format (e.g. `pixi-lock`)
2. Integrated user experience that does not rely on separate subcommands (e.g.
   lockfiles are create via `conda export` and a separate `conda-lock` command)

We see this project as an iteration on conda-lock while still keeping compatibility
with it. We hope this plugin will give conda users more options and flexibility when it
comes to sharing reproducible environments across the different tools available in our
ecosystem.