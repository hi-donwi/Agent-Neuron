# neuron-lab

The lab is the Python side of Agent-Neuron: it will build datasets, train neurons, and
evaluate them. The `neuron` binary calls it through a versioned JSON contract
([ADR-0005](../docs/adr/0005-pure-go-runtime-python-lab-external-engine.md)). A machine
that only serves neurons needs no Python and never installs this package.

Status: skeleton. The only command is `version`. Beside it are the building blocks the N0
spikes measure with (`neuron_lab.metrics`, `lexical`, `skillset`, `head`) and the spikes
themselves under `spikes/`. Each dependency arrives with the milestone that needs it
([ROADMAP](../ROADMAP.md)), pinned by `uv.lock`: `numpy` is the only runtime dependency so
far, and the `spikes` group adds what the spikes load models with.

## Working on it

The lab is managed by [uv](https://docs.astral.sh/uv/) and needs Python 3.12 or newer.

```bash
make lab-check
```

runs, from the repository root, exactly what CI runs: `uv sync --locked`, `ruff check`,
`ruff format --check`, and `pytest`. `--locked` fails when `uv.lock` no longer matches
`pyproject.toml`; after changing dependencies, run `uv lock` in this directory and commit
the lock file with the change.

```bash
cd lab && uv run python -m neuron_lab version --json
```

prints the lab version and the Python version it runs on.

## Spikes

A spike is a measurement, not a feature: one script under `spikes/`, a write-up under
[`docs/spikes/`](../docs/spikes/README.md), and no place in CI. Spikes need the `spikes` dependency
group, read models from the git-ignored `.neuron/` cache, and fetch nothing unless told to.

```bash
cd lab && uv run --locked --group spikes python -I spikes/router_quality.py --skills-repo <path> --download
```

runs Spike D, router quality. `<path>` is a clone of
[Agent-Skills](https://github.com/hi-donwi/Donwi-Skills) at any commit; the script extracts
the commit it pins. `--download` fetches about 265 MB of models and data on the first run,
each file at a pinned revision and checked against a pinned SHA-256; without it the script
stops and lists what is missing.
