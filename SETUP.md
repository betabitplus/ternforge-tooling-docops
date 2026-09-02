# Setup

Use this file to provision a local contributor environment. For day-to-day
workflow, tests, hooks, and release conventions, use
[CONTRIBUTING.md](CONTRIBUTING.md).

## Prerequisites

- Python 3.13+
- `uv` matching `[tool.uv].required-version` in `pyproject.toml`

## First-Time Setup

Run this from the repository root:

```bash
bash scripts/env/setup.sh
direnv allow
bash scripts/env/doctor.sh
```

`scripts/env/setup.sh` creates `uv.lock` only on the first bootstrap, then runs
strict `uv sync --locked --all-groups` and installs configured git hook types. `direnv allow` lets `.envrc` activate the local environment.
`scripts/env/doctor.sh` checks common local setup problems.

To install or refresh all configured hook stages directly, run:

```bash
uv run pre-commit install
```

## Running Through Direnv

If a shell has not loaded `.envrc`, run repo commands through `direnv exec .`:

```bash
direnv exec . uv run pytest tests/ternforge_docops -m hermetic -q
direnv exec . uv run pytest tests/ternforge_docops/integration/test_config_lifecycle.py -q --no-cov
```

## Devcontainer

The devcontainer provisions an in-container `.venv` through the same bootstrap-aware `scripts/env/setup.sh` contract.
VS Code points to `${workspaceFolder}/.venv/bin/python` inside the container.

If VS Code loses the interpreter, run `Python: Clear Workspace Interpreter Setting`
and reselect `ternforge-docops (.venv)`.

## Clean Rebuild With Uv

```bash
rm -rf .venv
rm -f uv.lock
uv cache clean
uv cache prune
uv lock
bash scripts/env/setup.sh
```
