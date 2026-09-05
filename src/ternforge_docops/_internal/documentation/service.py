"""Documentation build orchestration over already-produced evidence artifacts."""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Generator
from contextlib import chdir, contextmanager, suppress
from pathlib import Path

from sphinx.cmd.build import build_main

from ternforge_docops._internal.allure import curate_results, generate_reports
from ternforge_docops._internal.resources import shared_docs_dir_path

_EVIDENCE_SOURCE = "ternforge-test-evidence.rst"
_EVIDENCE_DIR = "_traceability"
_EVIDENCE_XML = "ternforge-test-evidence.xml"
_EVIDENCE_SOURCE_TEXT = (
    ":orphan:\n\n"
    "Test evidence\n"
    "=============\n\n"
    ".. test-file:: Imported test evidence\n"
    "   :id: TEST_EVIDENCE\n"
    f"   :file: {_EVIDENCE_DIR}/{_EVIDENCE_XML}\n"
    "   :auto_suites:\n"
    "   :auto_cases:\n"
)


def _run_sphinx(
    root: Path,
    docs_root: Path,
    output_root: Path,
    builder: str,
    *,
    live_examples: bool = False,
) -> None:
    """Run one strict Sphinx builder in the repository context."""
    arguments = ["-E", "-W", "--keep-going"]
    if not live_examples:
        arguments.extend(("-D", "plot_gallery=0"))
    if builder == "simplepdf":
        arguments.extend(("-D", "llms_txt_enabled=0"))
    arguments.extend(("-b", builder, str(docs_root), str(output_root)))
    with chdir(root):
        exit_code = build_main(arguments)
    if exit_code:
        message = f"Sphinx {builder} build failed with exit code {exit_code}"
        raise RuntimeError(message)


@contextmanager
def _materialized_sources(docs_root: Path, junit: Path | None) -> Generator[None]:
    """Materialize package-owned views and optional JUnit only for one build."""
    generated: list[Path] = []
    docs_root.mkdir(parents=True, exist_ok=True)

    for source in shared_docs_dir_path().glob("*.rst"):
        target = docs_root / source.name
        if target.exists():
            if target.read_bytes() == source.read_bytes():
                # Recover an exact package-owned copy left by an interrupted build.
                generated.append(target)
            continue
        target.write_bytes(source.read_bytes())
        generated.append(target)

    evidence_source = docs_root / _EVIDENCE_SOURCE
    trace_dir = docs_root / _EVIDENCE_DIR
    evidence_target = trace_dir / _EVIDENCE_XML

    # Interrupted local builds can be terminated before this context manager gets
    # a chance to clean its transient evidence files. Reconcile only DocOps-reserved
    # paths here so later builds neither import stale JUnit nor become wedged.
    if evidence_source.exists():
        if evidence_source.read_text(encoding="utf-8") != _EVIDENCE_SOURCE_TEXT:
            message = (
                f"DocOps reserved evidence source already exists: {evidence_source}"
            )
            raise RuntimeError(message)
        evidence_source.unlink()
    evidence_target.unlink(missing_ok=True)
    with suppress(OSError):
        trace_dir.rmdir()

    if junit is not None:
        junit = junit.resolve()
        if not junit.is_file():
            message = f"JUnit evidence does not exist: {junit}"
            raise FileNotFoundError(message)
        trace_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(junit, evidence_target)
        evidence_source.write_text(_EVIDENCE_SOURCE_TEXT, encoding="utf-8")
        generated.extend((evidence_source, evidence_target))

    try:
        yield
    finally:
        for path in reversed(generated):
            path.unlink(missing_ok=True)
        with suppress(OSError):
            trace_dir.rmdir()


def build_html(
    root: Path,
    *,
    docs: Path | None = None,
    output: Path | None = None,
    junit: Path | None = None,
    live_examples: bool = False,
) -> Path:
    """Build strict HTML documentation without executing project tests."""
    docs_root = docs or root / "docs"
    output_root = output or docs_root / "_build" / "html"
    with _materialized_sources(docs_root, junit):
        _run_sphinx(
            root,
            docs_root,
            output_root,
            "html",
            live_examples=live_examples,
        )
    return output_root


def build_dossier(
    root: Path,
    *,
    docs: Path | None = None,
    output: Path | None = None,
    junit: Path | None = None,
) -> Path:
    """Build the release dossier through the upstream SimplePDF Sphinx builder."""
    docs_root = docs or root / "docs"
    output_root = output or docs_root / "_build" / "dossier"
    with _materialized_sources(docs_root, junit):
        _run_sphinx(root, docs_root, output_root, "simplepdf")
    return output_root / "release-dossier.pdf"


def build_portal(
    root: Path,
    *,
    allure_results: Path,
    output: Path | None = None,
    junit: Path | None = None,
    live_examples: bool = False,
) -> Path:
    """Build docs plus Allure perspectives from pre-existing evidence inputs."""
    output_root = build_html(
        root,
        output=output,
        junit=junit,
        live_examples=live_examples,
    )
    needs_json = output_root / "needs.json"
    if not needs_json.is_file():
        message = f"Sphinx build did not produce {needs_json}"
        raise RuntimeError(message)

    with tempfile.TemporaryDirectory(prefix="ternforge-docops-allure-") as temp_dir:
        temp = Path(temp_dir)
        curated = temp / "curated"
        bdd = temp / "bdd"
        reports_root = temp / "reports"
        curate_results(
            allure_results,
            needs_json=needs_json,
            curated_results=curated,
            bdd_results=bdd,
        )
        reports = generate_reports(
            curated_results=curated,
            bdd_results=bdd,
            output_root=reports_root,
        )
        target = output_root / "test-results"
        shutil.rmtree(target, ignore_errors=True)
        for name, report in reports.items():
            destination = target / name
            destination.mkdir(parents=True, exist_ok=True)
            shutil.copy2(report, destination / "index.html")
        shutil.copy2(reports["requirements"], target / "index.html")
    return output_root
