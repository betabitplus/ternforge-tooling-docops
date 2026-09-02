# Ternforge DocOps

Language-agnostic documentation operations tooling for Ternforge repositories.
The implementation is a normal Ternforge Python tool, but the consumer contract is
CLI + Sphinx configuration + standard evidence artifacts, so repositories do not
need to be Python projects.

## Responsibilities

DocOps owns the reusable documentation platform layer:

- the canonical Sphinx-Needs engineering graph profile and schemas;
- the shared Sphinx extension stack and presentation styles;
- graph-native verification views over Sphinx-Needs/Test-Reports evidence;
- retained Engineering Experiment report validation and isolated capture;
- in-place experiment notebook mounting and publication of retained media inputs;
- Allure result curation and standard report perspectives;
- strict HTML, portal, and release-dossier build orchestration.

DocOps deliberately does **not** own test execution, CI runners, repository policy,
or language-specific test semantics. Test adapters produce evidence, `py-lib-policy`
owns repository laws, and `ternforge-infra-ci` owns workflow/runners/deployment.

## CLI

Materialize or verify the authoring resources needed by tools such as ubCode:

```bash
ternforge-docops sync
ternforge-docops check
```

Build documentation from already-produced project evidence:

```bash
ternforge-docops build html
ternforge-docops build portal --allure-results allure-results
ternforge-docops build dossier
```

`build portal` consumes Allure results; it never runs the project test suite.
`build dossier` delegates to the upstream Sphinx SimplePDF builder and therefore
requires the operating-system libraries required by WeasyPrint on the runner.

Validate or capture retained Engineering Experiments:

```bash
ternforge-docops experiments validate
ternforge-docops experiments capture 0001
```

Experiment execution is language-agnostic at the DocOps boundary. Each capsule
provides its own Jupyter kernelspec; DocOps executes the notebook through the
standard Jupyter protocol from an isolated temporary copy and validates the
captured report before replacing retained evidence.

## Sphinx Integration

A consumer enables the shared stack with the base extension:

```python
extensions = ["ternforge_docops._api.sphinx"]
```

Python libraries may additionally enable the Python adapter:

```python
extensions = [
    "ternforge_docops._api.sphinx",
    "ternforge_docops._api.sphinx_python",
]
```

The base extension owns the generic Sphinx-Needs/Test-Reports/MyST-NB/LLM/PDF
configuration. The Python adapter only adds Python-specific source/API/example
integration.

## Development

Provision the repository with the standard Ternforge environment bootstrap:

```bash
bash scripts/env/setup.sh
```

Run the main local checks:

```bash
uv run pytest
uv run ty check
uv run pyright
uv run lint-imports
uv run py-lib-policy check
uv run ternforge-docops build html
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for repository conventions and
[docs/README.md](docs/README.md) for documentation-specific development notes.
