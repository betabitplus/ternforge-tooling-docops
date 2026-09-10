"""Sphinx integration for retained Engineering Experiment reports."""

from __future__ import annotations

import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import nbformat
from nbformat import NotebookNode

from ternforge_docops._internal.experiments import discover_capsules
from ternforge_docops._internal.experiments.digest import capsule_digest

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.config import Config


_STEP_HEADING = re.compile(r"(?m)^## (?P<number>[1-9][0-9]*)\. (?P<title>\S.+)$")
_SECONDS_PER_MINUTE = 60
_MILLISECONDS_PER_SECOND = 1000


def _parse_timestamp(value: object) -> datetime | None:
    """Parse a Jupyter execution timestamp as UTC."""
    if not isinstance(value, str) or not value:
        return None
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError:
        return None
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC)


def _execution_window(cell: NotebookNode) -> tuple[datetime, datetime] | None:
    """Return the wall-clock execution window retained by nbclient."""
    execution = cell.metadata.get("execution", {})
    start = _parse_timestamp(
        execution.get("iopub.status.busy") or execution.get("iopub.execute_input")
    )
    end = _parse_timestamp(
        execution.get("iopub.status.idle") or execution.get("shell.execute_reply")
    )
    if start is None or end is None or end < start:
        return None
    return start, end


def _format_duration(seconds: float) -> str:
    """Format execution time compactly for a forensic details block."""
    if seconds < 1:
        return f"{round(seconds * _MILLISECONDS_PER_SECOND):d} ms"
    if seconds < _SECONDS_PER_MINUTE:
        return f"{seconds:.1f} s"
    minutes, whole_seconds = divmod(round(seconds), _SECONDS_PER_MINUTE)
    if minutes < _SECONDS_PER_MINUTE:
        return f"{minutes}m {whole_seconds:02d}s"
    hours, minutes = divmod(minutes, _SECONDS_PER_MINUTE)
    return f"{hours}h {minutes:02d}m"


def _step_label(step: NotebookNode, fallback: int) -> str:
    """Return the authored step heading used beside one evidence timing."""
    match = _STEP_HEADING.search(str(step.source))
    if match is None:
        return f"Step {fallback}"
    title = match.group("title").replace("|", r"\|")
    return f"{match.group('number')}. {title}"


def _freshness(capsule: Path, notebook: NotebookNode) -> str:
    """Return the retained capture freshness state."""
    stored = str(notebook.metadata.get("ternforge", {}).get("capsule_digest", ""))
    if not stored or stored == "UNSET":
        return "Unknown"
    return "Current" if stored == capsule_digest(capsule, notebook) else "Stale"


def _capture_summary(notebook: NotebookNode) -> list[str]:
    """Return compact capture-level timing facts."""
    windows = [
        window
        for cell in notebook.cells
        if cell.cell_type == "code" and (window := _execution_window(cell)) is not None
    ]
    if not windows:
        return []
    started = min(start for start, _ in windows)
    finished = max(end for _, end in windows)
    duration = _format_duration((finished - started).total_seconds())
    return [
        f"- **Captured:** {started:%Y-%m-%d %H:%M} UTC",
        f"- **Capture duration:** {duration}",
    ]


def _runtime_summary(notebook: NotebookNode) -> str | None:
    """Return one compact runtime fact when notebook metadata provides it."""
    language = str(notebook.metadata.get("language_info", {}).get("name", ""))
    version = str(notebook.metadata.get("language_info", {}).get("version", ""))
    kernel = str(notebook.metadata.get("kernelspec", {}).get("name", ""))
    runtime = " ".join(part for part in (language.title(), version) if part)
    if runtime and kernel:
        return f"- **Runtime:** {runtime} (`{kernel}`)"
    if runtime:
        return f"- **Runtime:** {runtime}"
    if kernel:
        return f"- **Kernel:** `{kernel}`"
    return None


def _step_timings(notebook: NotebookNode) -> list[tuple[str, str]]:
    """Return retained evidence-step durations."""
    timings: list[tuple[str, str]] = []
    for index, cell in enumerate(notebook.cells):
        tags = {str(tag) for tag in cell.metadata.get("tags", [])}
        if "exp-evidence" not in tags:
            continue
        window = _execution_window(cell)
        if window is None:
            continue
        step = notebook.cells[index - 1] if index else cell
        timings.append(
            (
                _step_label(step, len(timings) + 1),
                _format_duration((window[1] - window[0]).total_seconds()),
            )
        )
    return timings


def _run_details(capsule: Path, notebook: NotebookNode) -> str:
    """Build low-noise execution provenance from standard Jupyter metadata."""
    freshness = _freshness(capsule, notebook)
    lines = [":::{dropdown} Run details", ":icon: clock", ""]
    lines.extend(_capture_summary(notebook))
    runtime = _runtime_summary(notebook)
    if runtime is not None:
        lines.append(runtime)
    lines.append(f"- **Freshness:** {freshness}")

    timings = _step_timings(notebook)
    if timings:
        lines.extend(
            ("", "**Step timings**", "", "| Step | Duration |", "| --- | ---: |")
        )
        lines.extend(f"| {label} | {duration} |" for label, duration in timings)
    lines.extend(("", ":::"))

    if freshness != "Stale":
        return "\n".join(lines)
    warning = (
        ":::{warning}\n"
        "**Captured evidence is stale.** Causal capsule state changed after this "
        "run; recapture before relying on the observations below.\n"
        ":::\n\n"
    )
    return warning + "\n".join(lines)


def _presentation_report(app: Sphinx, capsule: Path, report: Path) -> Path:
    """Create a transient mounted notebook with low-noise execution provenance."""
    notebook = nbformat.read(report, as_version=4)
    if notebook.cells and notebook.cells[0].cell_type == "markdown":
        details = _run_details(capsule, notebook)
        source = str(notebook.cells[0].source).rstrip()
        notebook.cells[0].source = f"{source}\n\n{details}\n"
    target = (
        Path(app.doctreedir) / "ternforge-experiments" / capsule.name / "report.ipynb"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, target)
    return target


def configure_experiment_mounts(app: Sphinx, config: Config) -> None:
    """Mount transiently enriched captured notebooks using sphinx-mounts."""
    root = Path(app.confdir).resolve().parent
    mounts: list[dict[str, object]] = []
    for capsule in discover_capsules(root):
        report = capsule / "report" / "report.ipynb"
        if not report.is_file():
            continue
        presented = _presentation_report(app, capsule, report)
        mounts.append(
            {
                "files": [str(presented)],
                "mount_at": f"experiments/_generated/{capsule.name}",
                # MyST-NB materializes rich MIME outputs in the host build tree;
                # they are generated renderer resources, not source-path escapes.
                "path_check": "off",
            }
        )
    config.sources_from_toml = None
    config.mounts = mounts


def publish_experiment_inputs(app: Sphinx) -> None:
    """Publish retained media inputs beside mounted report pages."""
    root = Path(app.confdir).resolve().parent
    output_root = Path(app.outdir) / "experiments" / "_generated"
    for capsule in discover_capsules(root):
        source = capsule / "inputs"
        if not source.is_dir():
            continue
        target = output_root / capsule.name / "inputs"
        shutil.rmtree(target, ignore_errors=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)
