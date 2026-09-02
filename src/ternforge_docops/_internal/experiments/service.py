"""Discovery, validation, and isolated capture for Engineering Experiments."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import nbformat
from jupyter_client.kernelspec import KernelSpecManager
from jupyter_client.manager import KernelManager
from nbclient import NotebookClient

from ternforge_docops._internal.experiments.digest import capsule_digest
from ternforge_docops._internal.experiments.report import validate_report


def discover_capsules(root: Path) -> tuple[Path, ...]:
    """Return retained experiment capsules below a repository root."""
    experiments = root.resolve() / "experiments"
    return tuple(
        sorted(
            (path for path in experiments.glob("*/exp_*") if path.is_dir()),
            key=lambda path: path.relative_to(root.resolve()).as_posix(),
        )
    )


def resolve_capsule(root: Path, value: str) -> Path:
    """Resolve an EXP number or capsule directory name uniquely."""
    capsules = discover_capsules(root)
    normalized = value.lower().removeprefix("exp_")
    if normalized.isdigit():
        prefix = f"exp_{int(normalized):04d}_"
        matches = [path for path in capsules if path.name.startswith(prefix)]
    else:
        matches = [path for path in capsules if path.name == value]
    if len(matches) != 1:
        message = (
            f"Expected exactly one experiment capsule for {value!r}; "
            f"found {len(matches)}"
        )
        raise ValueError(message)
    return matches[0]


def validate_experiments(root: Path) -> dict[Path, list[str]]:
    """Return report violations keyed by capsule."""
    return {
        capsule: errors
        for capsule in discover_capsules(root)
        if (errors := validate_report(capsule))
    }


def _copy_capsule(source: Path, destination: Path) -> None:
    """Copy causal capsule state while excluding ephemeral execution caches."""
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns(
            ".git",
            ".ipynb_checkpoints",
            ".venv",
            "__pycache__",
            "*.pyc",
        ),
    )


def _capture_environment() -> dict[str, str]:
    """Return a sanitized environment for the capsule-owned kernel process."""
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment.pop("VIRTUAL_ENV", None)
    for name in tuple(environment):
        if name.startswith("DIRENV_"):
            environment.pop(name)
    return environment


def _execute_report(capsule: Path) -> None:
    """Execute a report through the capsule-owned Jupyter kernelspec."""
    report = capsule / "report" / "report.ipynb"
    notebook = nbformat.read(report, as_version=4)
    kernelspec = str(notebook.metadata.get("kernelspec", {}).get("name", ""))
    if not kernelspec:
        message = "report must declare notebook.metadata.kernelspec.name"
        raise ValueError(message)
    kernel_root = capsule / "jupyter" / "kernels"
    kernel = kernel_root / kernelspec / "kernel.json"
    if not kernel.is_file():
        message = f"capsule-owned kernelspec is missing: {kernel.relative_to(capsule)}"
        raise ValueError(message)

    spec_manager = KernelSpecManager(kernel_dirs=[str(kernel_root)])
    kernel_manager = KernelManager(
        kernel_name=kernelspec,
        kernel_spec_manager=spec_manager,
    )
    client = NotebookClient(
        notebook,
        km=kernel_manager,
        kernel_name=kernelspec,
        resources={"metadata": {"path": report.parent}},
        timeout=1800,
    )
    client.execute(env=_capture_environment())
    nbformat.write(notebook, report)


def capture_experiment(capsule: Path) -> None:
    """Capture one report from an isolated temporary capsule copy."""
    capsule = capsule.resolve()
    with tempfile.TemporaryDirectory(prefix=f"{capsule.name}-") as temp_dir:
        isolated = Path(temp_dir) / capsule.name
        _copy_capsule(capsule, isolated)
        _execute_report(isolated)

        report = isolated / "report" / "report.ipynb"
        notebook = nbformat.read(report, as_version=4)
        notebook.metadata.setdefault("ternforge", {})["capsule_digest"] = (
            capsule_digest(isolated, notebook)
        )
        nbformat.write(notebook, report)

        errors = validate_report(isolated)
        if errors:
            message = "Captured report is invalid:\n" + "\n".join(
                f"- {error}" for error in errors
            )
            raise ValueError(message)

        shutil.copy2(report, capsule / "report" / "report.ipynb")
        isolated_artifacts = isolated / "artifacts"
        target_artifacts = capsule / "artifacts"
        if isolated_artifacts.is_dir():
            if target_artifacts.exists():
                shutil.rmtree(target_artifacts)
            shutil.copytree(isolated_artifacts, target_artifacts)
