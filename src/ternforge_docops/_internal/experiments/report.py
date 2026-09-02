"""Notebook contract validation for retained Engineering Experiments."""

from __future__ import annotations

import re
from pathlib import Path

import nbformat
from nbformat import NotebookNode

from ternforge_docops._internal.experiments.digest import capsule_digest

_CAPSULE_PATTERN = re.compile(r"^exp_(?P<number>[0-9]{4})_[a-z0-9_]+$")
_ID_PATTERN = re.compile(r"^EXP_[0-9]{4}$")
_STEP_PATTERN = re.compile(r"^## (?P<number>[1-9][0-9]*)\. (?P<title>\S.+)$")
_MIN_REPORT_CELLS = 5
_ROLE_TAGS = {
    "exp-meta",
    "exp-question",
    "exp-setup",
    "exp-step",
    "exp-evidence",
    "exp-conclusion",
}


def _tags(cell: NotebookNode) -> set[str]:
    """Return normalized notebook-cell tags."""
    return {str(tag) for tag in cell.metadata.get("tags", [])}


def _role(cell: NotebookNode) -> str:
    """Resolve the single DocOps experiment role assigned to a cell."""
    roles = _tags(cell) & _ROLE_TAGS
    if len(roles) != 1:
        message = f"expected exactly one experiment role tag, got {sorted(roles)}"
        raise ValueError(message)
    return next(iter(roles))


def _extract_need_id(source: str) -> str | None:
    """Extract the retained EXP Need identifier from metadata Markdown."""
    match = re.search(r"(?m)^:id:\s*(EXP_[0-9]{4})\s*$", source)
    return None if match is None else match.group(1)


def _validate_roles(notebook: NotebookNode) -> list[str]:
    """Validate the strict Meta/Question/Setup/(Step/Evidence)+/Conclusion order."""
    errors: list[str] = []
    roles: list[str] = []
    for index, cell in enumerate(notebook.cells):
        try:
            roles.append(_role(cell))
        except ValueError as exc:
            errors.append(f"cell {index}: {exc}")
    if errors:
        return errors

    if roles[:3] != ["exp-meta", "exp-question", "exp-setup"] or roles[-1] != (
        "exp-conclusion"
    ):
        errors.append("report must start Meta -> Question -> Setup and end Conclusion")
    middle = roles[3:-1]
    if not middle or len(middle) % 2:
        errors.append("report must contain one or more Step -> Evidence pairs")
        return errors
    for index in range(0, len(middle), 2):
        if middle[index : index + 2] != ["exp-step", "exp-evidence"]:
            errors.append("report body must repeat Step -> Evidence in strict order")
            break
    return errors


def _validate_meta_id(capsule: Path, source: str) -> list[str]:
    """Validate that retained EXP metadata identity matches the capsule path."""
    errors: list[str] = []
    if source.count("```{exp}") != 1:
        errors.append("metadata cell must contain exactly one EXP need")
    need_id = _extract_need_id(source)
    if need_id is None or not _ID_PATTERN.fullmatch(need_id):
        errors.append("metadata cell must declare :id: EXP_####")
    else:
        match = _CAPSULE_PATTERN.fullmatch(capsule.name)
        expected = f"EXP_{match.group('number')}" if match else ""
        if need_id != expected:
            errors.append(f"path/id mismatch: expected {expected}, found {need_id}")
    return errors


def _validate_meta_fields(source: str) -> list[str]:
    """Validate required and obsolete fields in retained EXP metadata."""
    errors: list[str] = []
    if ":experiment_date:" not in source:
        errors.append("EXP metadata must declare experiment_date")
    if "**Question.**" not in source or "**Conclusion.**" not in source:
        errors.append("EXP content must include Question and Conclusion summaries")
    errors.extend(
        f"obsolete EXP metadata field is forbidden: {field}"
        for field in (":experiment_source:", ":experiment_evidence:")
        if field in source
    )
    return errors


def _validate_meta(capsule: Path, cell: NotebookNode) -> list[str]:
    """Validate the retained EXP metadata cell and capsule identity."""
    if cell.cell_type != "markdown":
        return ["metadata cell must be Markdown"]
    source = str(cell.source)
    return [*_validate_meta_id(capsule, source), *_validate_meta_fields(source)]


def _validate_sections(notebook: NotebookNode) -> list[str]:
    """Validate Question, Setup, and Conclusion section contracts."""
    errors: list[str] = []
    question = notebook.cells[1]
    setup = notebook.cells[2]
    conclusion = notebook.cells[-1]
    if question.cell_type != "markdown" or not str(question.source).startswith(
        "## Question\n"
    ):
        errors.append("Question cell must start with '## Question'")
    if setup.cell_type != "code" or "hide-input" not in _tags(setup):
        errors.append("Setup must be hidden code")
    elif setup.execution_count != 1:
        errors.append("Setup must be execution_count 1; recapture linearly")
    if conclusion.cell_type != "markdown" or not str(conclusion.source).startswith(
        "## Conclusion\n"
    ):
        errors.append("Conclusion cell must start with '## Conclusion'")
    return errors


def _validate_evidence_cell(
    evidence: NotebookNode,
    *,
    step_number: int,
    expected_execution: int,
) -> list[str]:
    """Validate one captured Step evidence cell and its execution state."""
    errors: list[str] = []
    if evidence.cell_type != "code":
        return [f"step {step_number} evidence must be a code cell"]
    if "hide-input" not in _tags(evidence):
        errors.append(f"step {step_number} evidence must use hide-input")
    if evidence.execution_count != expected_execution:
        errors.append(
            f"step {step_number} evidence must have execution_count "
            f"{expected_execution}"
        )
    if not evidence.outputs:
        errors.append(f"step {step_number} has no captured evidence output")
    has_error = any(output.get("output_type") == "error" for output in evidence.outputs)
    if has_error and "raises-exception" not in _tags(evidence):
        errors.append(f"step {step_number} captured an unmarked error")
    return errors


def _validate_steps(notebook: NotebookNode) -> list[str]:
    """Validate numbered Step/Evidence pairs and linear execution counts."""
    errors: list[str] = []
    for step_number, index in enumerate(
        range(3, len(notebook.cells) - 1, 2),
        start=1,
    ):
        step = notebook.cells[index]
        evidence = notebook.cells[index + 1]
        heading = str(step.source).splitlines()[0] if step.source else ""
        match = _STEP_PATTERN.fullmatch(heading)
        if (
            step.cell_type != "markdown"
            or match is None
            or int(match.group("number")) != step_number
        ):
            errors.append(
                f"step {step_number} must start with '## {step_number}. <title>'"
            )
        errors.extend(
            _validate_evidence_cell(
                evidence,
                step_number=step_number,
                expected_execution=step_number + 1,
            )
        )
    return errors


def _validate_kernel(capsule: Path, notebook: NotebookNode) -> list[str]:
    """Require a notebook kernelspec owned by the retained experiment capsule."""
    name = str(notebook.metadata.get("kernelspec", {}).get("name", ""))
    if not name:
        return ["report must declare notebook.metadata.kernelspec.name"]
    path = capsule / "jupyter" / "kernels" / name / "kernel.json"
    if not path.is_file():
        return [f"capsule-owned kernelspec is missing: {path.relative_to(capsule)}"]
    return []


def validate_report(capsule: Path) -> list[str]:
    """Return report-contract violations for one experiment capsule."""
    report = capsule / "report" / "report.ipynb"
    if not report.is_file():
        return ["missing report/report.ipynb"]
    try:
        notebook = nbformat.read(report, as_version=4)
        nbformat.validate(notebook)
    except Exception as exc:
        return [f"invalid notebook: {exc}"]
    if len(notebook.cells) < _MIN_REPORT_CELLS:
        return [
            (
                "report is too short for Meta -> Question -> Setup -> "
                "Evidence -> Conclusion"
            )
        ]

    errors = [
        *_validate_roles(notebook),
        *_validate_meta(capsule, notebook.cells[0]),
        *_validate_sections(notebook),
        *_validate_steps(notebook),
        *_validate_kernel(capsule, notebook),
    ]
    stored = str(notebook.metadata.get("ternforge", {}).get("capsule_digest", ""))
    actual = capsule_digest(capsule, notebook)
    if not stored or stored == "UNSET":
        errors.append("missing captured ternforge.capsule_digest")
    elif stored != actual:
        errors.append("capsule digest is stale; causal capsule state changed")
    return errors
