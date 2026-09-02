---
name: docs
doc_type: index
description: Repository documentation entry point for API reference and executable examples.
---

# Documentation

The committed documentation surface is intentionally small before project-specific
requirements and architecture are modeled explicitly.

- `api.md` defines the generated public API reference.
- `examples/ternforge_docops/` is the source of truth for runnable workflows.
- `traceability.rst` renders implementation and verification evidence from Sphinx-Needs.

## Build

Traceability builds need current pytest evidence. Generate the gitignored local JUnit
with the same hermetic contract as required CI, then build without executing live examples:

```bash
uv run pytest -c pyproject.toml -n 2 \
    --record-mode=none \
    --block-network \
    --allowed-hosts='localhost,127\\.0\\.0\\.1' \
    --cov-context=test \
    --junitxml=docs/_traceability/local-pytest.xml
uv run sphinx-build -W --keep-going -D plot_gallery=0 -b html docs docs/_build/html
```

The full live gallery uses the same local JUnit prerequisite and additionally requires
the configured environment and credentials:

```bash
uv run sphinx-build -W --keep-going -b html docs docs/_build/html
```

Required CI performs the JUnit import automatically before its documentation build.

Open `docs/_build/html/index.html` in a browser to inspect the generated site.
