---
name: docs
doc_type: index
description: Development notes for the Ternforge DocOps documentation site.
---

# Documentation

The DocOps repository self-hosts the documentation stack that it ships to
consumers. Its own site is therefore an acceptance surface for the base Sphinx
extension, Python adapter, canonical engineering graph resources, shared styles,
and build commands.

## Build HTML

```bash
uv run ternforge-docops build html
```

The command performs a strict Sphinx build (`-W --keep-going`) with gallery
execution disabled. It does not execute the project test suite. Generated output
is written to `docs/_build/html/`, including `needs.json`, `llms.txt`, and
`llms-full.txt`.

## Build The Release Dossier

```bash
uv run ternforge-docops build dossier
```

This delegates PDF generation to the upstream SimplePDF Sphinx builder. The local
machine or CI runner must provide the operating-system libraries required by
WeasyPrint. DocOps does not install or emulate those system dependencies.

## Engineering Experiments

Validate retained experiment reports with:

```bash
uv run ternforge-docops experiments validate
```

Capture one experiment through its capsule-owned Jupyter kernelspec with:

```bash
uv run ternforge-docops experiments capture 0001
```

Capture executes from an isolated temporary capsule copy and only replaces the
retained report/artifacts after the result passes the DocOps report and freshness
contract.

## Graph Resources

Materialize the canonical graph resources used by repository authoring tools:

```bash
uv run ternforge-docops sync
uv run ternforge-docops check
```

Sphinx itself reads the canonical graph profile directly from the installed DocOps
package. The materialized `.ternforge/docops/` copy exists for filesystem-based
authoring tools such as ubCode, not as a second source of truth.
