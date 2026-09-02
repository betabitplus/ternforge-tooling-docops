# Ternforge DocOps

Language-agnostic documentation operations tooling for Ternforge repositories.

This project uses the Ternforge Python-library structure: source-layout
packaging, a small public package boundary, private implementation folders,
runnable public API examples, optional isolated engineering experiments, and
reusable project tooling.

## What It Provides

- `src/` source-layout packaging.
- A stable top-level public package entrypoint.
- `_api` declarations over private `_internal` implementation.
- A reusable config lifecycle with public re-exports and private snapshot state.
- Structured logging plus safe error/value previews from `py-lib-runtime`.
- Reusable development and test tooling through `py-lib-testkit`.
- Package-specific tests under `tests/ternforge_docops/` without a mandatory test taxonomy.
- Runnable public API examples under `examples/ternforge_docops/`.
- Optional isolated Engineering Experiment capsules under `experiments/`.
- Public API and executable-example documentation under `docs/`.
- Shared tooling metadata in `[tool.ternforge]`.
- Import-linter, offline example-import checks, and generated Sphinx documentation.

The package starts with the common public boundary used across the py
libraries: version metadata, a package base error, config install/read helpers,
and a validated config snapshot type.

```python
from ternforge_docops import DocOpsConfig, get_config, install_config

config = install_config(DocOpsConfig())
assert get_config() is config
```

Add product-specific facades, DTOs, defaults, and vocabulary only when the
library has real behavior to ship.

## Quickstart

```bash
bash scripts/env/setup.sh
uv run pytest
```

After the first render, review project metadata, repository URLs, environment
prefixes, and the first real public behavior slice before treating the package
as ready for product work.

## Project Customization

Review these project-specific values first:

- Distribution name: `ternforge-docops`
- Import package: `ternforge_docops`
- Public API objects in `src/ternforge_docops/__init__.py`
- Repository docs under `docs/`
- Package tests under `tests/ternforge_docops/`
- Runnable examples under `examples/ternforge_docops/`
- Optional isolated experiment capsules under `experiments/`
- Project URLs in `pyproject.toml`
- Environment prefix: `TERNFORGE_DOCOPS`
- Optional `[tool.py_lib_runtime.logging]` policy if local runs need
  non-default logging levels or quiet third-party modules

## Documentation

Start with [docs/README.md](docs/README.md) for the generated site, live examples,
and API reference.
