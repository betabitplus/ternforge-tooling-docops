"""Causal digest calculation for retained Engineering Experiments."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from nbformat import NotebookNode

_EPHEMERAL_PARTS = {
    ".git",
    ".ipynb_checkpoints",
    ".venv",
    "__pycache__",
    "artifacts",
}
_PRESENTATION_FUNCTIONS = {
    "_html_value",
    "_rendered_value",
    "_facts_markdown",
    "_input_facts",
    "display_case_input",
    "display_case_code",
    "_short_text",
    "_summary_items",
    "display_result",
}


def _update(hasher: hashlib._Hash, marker: bytes, data: bytes) -> None:
    """Add one length-delimited record to a digest."""
    hasher.update(len(marker).to_bytes(8, "big"))
    hasher.update(marker)
    hasher.update(len(data).to_bytes(8, "big"))
    hasher.update(data)


def _python_semantics(source: str, *, filename: str) -> bytes:
    """Return formatter/comment-insensitive Python syntax."""
    tree = ast.parse(source, filename=filename, type_comments=True)
    return ast.dump(tree, include_attributes=False).encode()


def _experiment_semantics(source: str, *, filename: str) -> bytes:
    """Return causal experiment syntax while ignoring report-only presentation helpers.

    Presentation-only helpers do not invalidate retained provider evidence.
    """
    tree = ast.parse(source, filename=filename, type_comments=True)
    body: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and (
            node.name in _PRESENTATION_FUNCTIONS
        ):
            continue
        if isinstance(node, ast.ImportFrom) and node.module == "IPython.display":
            continue
        if isinstance(node, ast.Import):
            aliases = [alias for alias in node.names if alias.name != "html"]
            if not aliases:
                continue
            node.names = aliases
        body.append(node)
    tree.body = body
    return ast.dump(tree, include_attributes=False).encode()


def _file_bytes(path: Path) -> bytes:
    """Return semantic bytes for Python and exact bytes for other files."""
    if path.suffix == ".py":
        source = path.read_text()
        if path.name == "experiment.py":
            return _experiment_semantics(source, filename=str(path))
        return _python_semantics(source, filename=str(path))
    return path.read_bytes()


def _causal_files(capsule: Path) -> tuple[Path, ...]:
    """Return capsule files that can influence a capture."""
    report = capsule / "report" / "report.ipynb"
    files = []
    for path in capsule.rglob("*"):
        if not path.is_file() or path == report:
            continue
        relative = path.relative_to(capsule)
        if any(part in _EPHEMERAL_PARTS for part in relative.parts):
            continue
        if path.suffix == ".pyc" or path.name == ".DS_Store":
            continue
        files.append(path)
    return tuple(sorted(files, key=lambda item: item.relative_to(capsule).as_posix()))


def capsule_digest(capsule: Path, notebook: NotebookNode) -> str:
    """Return a digest of causal capsule state and executable notebook cells."""
    hasher = hashlib.sha256()
    for path in _causal_files(capsule):
        relative = path.relative_to(capsule).as_posix().encode()
        _update(hasher, relative, _file_bytes(path))

    language = str(
        notebook.metadata.get("language_info", {}).get("name")
        or notebook.metadata.get("kernelspec", {}).get("language")
        or ""
    ).lower()
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type != "code":
            continue
        source = str(cell.source)
        data = (
            _python_semantics(source, filename=f"report-code:{index}")
            if language == "python"
            else source.encode()
        )
        _update(hasher, f"report-code:{index}".encode(), data)
    return hasher.hexdigest()
