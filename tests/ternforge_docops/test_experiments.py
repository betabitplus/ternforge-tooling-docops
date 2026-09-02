"""Hermetic Engineering Experiment validation and capture tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import nbformat

from ternforge_docops._internal.experiments import (
    capture_experiment,
    validate_report,
)


def _cell(cell: nbformat.NotebookNode, *tags: str) -> nbformat.NotebookNode:
    cell.metadata["tags"] = list(tags)
    return cell


def _make_capsule(tmp_path: Path) -> Path:
    capsule = tmp_path / "experiments" / "demo" / "exp_0001_demo"
    report_dir = capsule / "report"
    kernel_dir = capsule / "jupyter" / "kernels" / "ternforge-exp"
    source_dir = capsule / "src"
    report_dir.mkdir(parents=True)
    kernel_dir.mkdir(parents=True)
    source_dir.mkdir(parents=True)

    (source_dir / "probe.py").write_text("VALUE = 1\n", encoding="utf-8")
    (kernel_dir / "kernel.json").write_text(
        json.dumps(
            {
                "argv": [
                    sys.executable,
                    "-m",
                    "ipykernel_launcher",
                    "-f",
                    "{connection_file}",
                ],
                "display_name": "Ternforge test experiment",
                "language": "python",
            }
        ),
        encoding="utf-8",
    )
    notebook = nbformat.v4.new_notebook(
        metadata={
            "kernelspec": {
                "display_name": "Ternforge test experiment",
                "language": "python",
                "name": "ternforge-exp",
            },
            "language_info": {"name": "python"},
            "ternforge": {"capsule_digest": "UNSET"},
        },
        cells=[
            _cell(
                nbformat.v4.new_markdown_cell(
                    """```{exp} Demo experiment
:id: EXP_0001
:experiment_date: 2026-09-02

**Question.** Can the capsule execute through its own kernelspec?

**Conclusion.** The captured output answers the question.
```
"""
                ),
                "exp-meta",
            ),
            _cell(
                nbformat.v4.new_markdown_cell(
                    "## Question\n\nCan the capsule execute through its own kernelspec?"
                ),
                "exp-question",
            ),
            _cell(
                nbformat.v4.new_code_cell("value = 41"),
                "exp-setup",
                "hide-input",
            ),
            _cell(
                nbformat.v4.new_markdown_cell("## 1. Observe output\n\nRun the probe."),
                "exp-step",
            ),
            _cell(
                nbformat.v4.new_code_cell("print(value + 1)"),
                "exp-evidence",
                "hide-input",
            ),
            _cell(
                nbformat.v4.new_markdown_cell(
                    "## Conclusion\n\nThe stored output is the retained evidence."
                ),
                "exp-conclusion",
            ),
        ],
    )
    nbformat.write(notebook, report_dir / "report.ipynb")
    return capsule


def test_capture_uses_capsule_owned_jupyter_kernel(tmp_path: Path) -> None:
    """Capture executes in isolation and leaves a valid retained report."""
    capsule = _make_capsule(tmp_path)

    capture_experiment(capsule)

    notebook = nbformat.read(capsule / "report" / "report.ipynb", as_version=4)
    assert validate_report(capsule) == []
    assert notebook.cells[2].execution_count == 1
    assert notebook.cells[4].execution_count == 2
    assert notebook.cells[4].outputs[0]["text"] == "42\n"


def test_digest_ignores_python_comments_but_detects_semantic_changes(
    tmp_path: Path,
) -> None:
    """Python formatting comments are non-causal while syntax changes are causal."""
    capsule = _make_capsule(tmp_path)
    source = capsule / "src" / "probe.py"
    capture_experiment(capsule)

    source.write_text("# prose only\nVALUE = 1\n", encoding="utf-8")
    assert validate_report(capsule) == []

    source.write_text("VALUE = 2\n", encoding="utf-8")
    assert validate_report(capsule) == [
        "capsule digest is stale; causal capsule state changed"
    ]
