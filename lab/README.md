# neuron-lab

The lab is the Python side of Agent-Neuron: it will build datasets, train neurons, and
evaluate them. The `neuron` binary calls it through a versioned JSON contract
([ADR-0005](../docs/adr/0005-pure-go-runtime-python-lab-external-engine.md)). A machine
that only serves neurons needs no Python and never installs this package.

Status: skeleton. The only command is `version`. The lab declares no machine-learning
dependency yet; each one arrives with the milestone that needs it
([ROADMAP](../ROADMAP.md)), pinned by `uv.lock`.

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
