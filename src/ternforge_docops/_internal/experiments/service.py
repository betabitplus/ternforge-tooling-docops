"""Discovery, validation, and isolated capture for Engineering Experiments."""

from __future__ import annotations

import json
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


def _transaction_dir(capsule: Path) -> Path:
    """Return the sibling transaction directory used for retained capture commit."""
    return capsule.parent / f".{capsule.name}.capture-transaction"


def _write_transaction_state(
    transaction: Path,
    *,
    phase: str,
    had_artifacts: bool,
) -> None:
    """Persist transaction state through an atomic same-filesystem rename."""
    temporary = transaction / "state.json.tmp"
    temporary.write_text(
        json.dumps({"phase": phase, "had_artifacts": had_artifacts}),
        encoding="utf-8",
    )
    temporary.replace(transaction / "state.json")


def _recover_capture_transaction(capsule: Path) -> None:
    """Rollback an interrupted retained-capture commit or finish cleanup."""
    transaction = _transaction_dir(capsule)
    if not transaction.exists():
        return

    state_path = transaction / "state.json"
    if not state_path.is_file():
        shutil.rmtree(transaction)
        return

    state = json.loads(state_path.read_text(encoding="utf-8"))
    if state.get("phase") == "committed":
        shutil.rmtree(transaction)
        return

    target_report = capsule / "report" / "report.ipynb"
    old_report = transaction / "old-report.ipynb"
    if old_report.is_file():
        old_report.replace(target_report)

    target_artifacts = capsule / "artifacts"
    displaced_artifacts = transaction / "old-artifacts"
    if bool(state.get("had_artifacts")):
        if displaced_artifacts.is_dir():
            if target_artifacts.exists():
                shutil.rmtree(target_artifacts)
            displaced_artifacts.replace(target_artifacts)
    elif target_artifacts.exists():
        shutil.rmtree(target_artifacts)

    shutil.rmtree(transaction)


def validate_experiments(root: Path) -> dict[Path, list[str]]:
    """Return report violations keyed by capsule, recovering interrupted commits."""
    violations: dict[Path, list[str]] = {}
    for capsule in discover_capsules(root):
        _recover_capture_transaction(capsule)
        errors = validate_report(capsule)
        if errors:
            violations[capsule] = errors
    return violations


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


def _commit_capture(capsule: Path, isolated: Path) -> None:
    """Commit report and artifacts as one recoverable retained-capture transaction."""
    _recover_capture_transaction(capsule)
    transaction = _transaction_dir(capsule)
    transaction.mkdir()

    target_report = capsule / "report" / "report.ipynb"
    target_artifacts = capsule / "artifacts"
    if target_artifacts.exists() and not target_artifacts.is_dir():
        message = f"experiment artifacts path is not a directory: {target_artifacts}"
        raise ValueError(message)

    shutil.copy2(target_report, transaction / "old-report.ipynb")
    shutil.copy2(isolated / "report" / "report.ipynb", transaction / "new-report.ipynb")

    isolated_artifacts = isolated / "artifacts"
    if isolated_artifacts.is_dir():
        shutil.copytree(isolated_artifacts, transaction / "new-artifacts")

    had_artifacts = target_artifacts.is_dir()
    _write_transaction_state(
        transaction,
        phase="prepared",
        had_artifacts=had_artifacts,
    )

    try:
        (transaction / "new-report.ipynb").replace(target_report)
        _write_transaction_state(
            transaction,
            phase="report-replaced",
            had_artifacts=had_artifacts,
        )

        if had_artifacts:
            target_artifacts.replace(transaction / "old-artifacts")
        staged_artifacts = transaction / "new-artifacts"
        if staged_artifacts.is_dir():
            staged_artifacts.replace(target_artifacts)

        _write_transaction_state(
            transaction,
            phase="committed",
            had_artifacts=had_artifacts,
        )
    except Exception:
        _recover_capture_transaction(capsule)
        raise

    shutil.rmtree(transaction)


def capture_experiment(capsule: Path) -> None:
    """Capture one report from an isolated temporary capsule copy."""
    capsule = capsule.resolve()
    _recover_capture_transaction(capsule)
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

        _commit_capture(capsule, isolated)
