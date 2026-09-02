# Contributing

Start with [SETUP.md](SETUP.md) to provision the local environment. If your
local environment feels off, run `bash scripts/env/doctor.sh` before debugging
deeper.

Use [docs/ternforge_docops/README.md](docs/ternforge_docops/README.md) for package
docs.

Repository-wide package and reusable-zone checks read metadata from
`[tool.ternforge]` in `pyproject.toml`. When repo-local scripts or shared
test support need package names or env-var prefixes, use
`py_lib_testkit.get_project_tooling_config` instead of hardcoding them.

`py-lib-runtime` is consumed as a runtime dependency, while `py-lib-policy`
and `py-lib-testkit` are independent development dependencies. Each package is
owned and released separately by Ternforge and pinned immutably by this repo. Keep this repo thin: import shared runtime helpers, call
shared console commands, and import shared test helpers instead of copying
reusable implementation files locally.

## Branch And Target Flow

Use a topic branch and land changes through a pull request to `main`.

## Local Validation

Run commit-time hooks:

```bash
uv run pre-commit run --all-files
```

Run push-time hooks:

```bash
uv run pre-commit run --all-files --hook-stage pre-push
```

## Template And Tooling Updates

Check whether this repo is behind the released Ternforge template:

```bash
uvx --from copier==9.17.2 copier check-update
```

Apply the latest released Ternforge template:

```bash
uvx --from copier==9.17.2 copier update
```

The update command leaves product-owned `src/`, `tests/`, `docs/`,
`examples/`, and `experiments/` files alone by default. Review the resulting
diff, run validation, then land the update through the normal pull request to `main`.

## Running Tests

Run the package test suite:

```bash
uv run pytest tests/ternforge_docops
```

Run only hermetic tests:

```bash
uv run pytest tests/ternforge_docops -m hermetic
```

Run all tests:

```bash
uv run pytest
```

## Running Tests Directly

If you run test files directly, ensure the repo root is on `PYTHONPATH`.
The tracked `.envrc` configures this automatically for direnv-aware shells.

## Runnable Examples

`examples/` is for committed public API demonstrations. Add an example when a
complete caller flow is clearer as a real Python file than as a short docs
snippet.

Run an example directly:

```bash
direnv exec . uv run python examples/ternforge_docops/<module>.py
```

Keep examples focused on imports from `ternforge_docops`. If an example
needs private modules, convert that behavior into a test or keep the investigation
temporary; a retained Engineering Experiment must stay independent of the shipped
package.

Every committed example should have a matching link from the package usage docs.
The examples smoke test discovers and runs committed example scripts so
docs examples do not drift silently.

## Engineering Experiments

`experiments/` is optional and contains durable investigations, not another test
suite or a home for ad-hoc scripts. Preserve an investigation only when its exact
inputs, executable method, environment, and captured result are useful engineering
knowledge.

Each retained experiment is a self-contained capsule under
`experiments/<project>/exp_####_<slug>/` with `src/experiment.py`, one captured
`report/report.ipynb`, its own `pyproject.toml`, `uv.lock`, and `.python-version`,
plus causal `inputs/` and optional retained `artifacts/` when needed.

Capsules are standalone uv projects. They must not import the parent package,
repository `src/` or `tests/`, sibling experiments, or shared experiment helpers,
and they must not use local/workspace/editable dependencies. `py-lib-policy`
enforces these reusable structural boundaries. Project-specific capture, report,
and documentation tooling may add stricter rules locally.

## Commit And Release Conventions

Commitizen validates local commit messages. Release Please owns project version,
changelog, release tags, and release pull requests. Commit messages and pull
request titles must follow [Conventional Commits](https://www.conventionalcommits.org/)
format, for example `feat: add retry policy`, `fix(cache): preserve metadata`,
or `chore(ci): update workflows`. Use GitHub's draft state instead of a `WIP`
title prefix.

For every pull request to `main`, choose the title according to
the highest release impact it contains: breaking change first, then `feat`,
then `fix`, otherwise an appropriate non-release type such as `docs` or
`chore`. CI validates the format, while the maintainer remains responsible for
choosing the correct semantic type.

Full CI runs on every pull request targeting `main`. Merges to `main` run the release workflow.
