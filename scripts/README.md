# Scripts

Repo-local scripts live here only when the implementation is specific to this
repository. Shared development commands come from `py-lib-testkit` console
scripts.

## Shared Repo Config

`py_lib_testkit.get_project_tooling_config` is the single reader for repo-local tooling
metadata in `[tool.ternforge]` in `pyproject.toml`.

- Use it when behavior depends on the distribution name, the primary package,
  the package list, or the env var prefix.
- Do not hardcode project package names in reusable checks, smokes, or shared
  test support; read them from `[tool.ternforge]`.
- When the template is rendered or updated for another library, keep
  `[project].name` and `[tool.ternforge]` in `pyproject.toml` accurate; the
  shared checks and smoke commands should then follow that config.
- `package_names` supports future multi-package repos; `primary_package`
  remains the default import/smoke target.
- Keep this helper out of runtime package code under `src/`; it is only for
  repository tooling and test support.

Example:

```python
from py_lib_testkit import get_project_tooling_config

project_config = get_project_tooling_config()
package_name = project_config.primary_package
package_names = project_config.package_names
```

## Local Scripts

- `env/`
  Local contributor environment setup and health checks. Every repository keeps `secrets.sh`; `.envrc` always invokes it.
  Repos that declare `[tool.ternforge.secrets].env_files` load encrypted
  dotenv secrets through `scripts/env/secrets.sh`.

Use shared smoke commands directly:

```bash
uv build
uv run pytest tests/ternforge_docops/integration/test_config_lifecycle.py -q --no-cov
```

Check and apply released Ternforge template updates with Copier:

```bash
uvx --from copier==9.17.2 copier check-update
uvx --from copier==9.17.2 copier update
```

Run structural and artifact checks directly when needed:

```bash
uv run py-lib-policy .
uv build
```
