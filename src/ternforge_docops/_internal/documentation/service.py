"""Documentation build orchestration over already-produced evidence artifacts."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from ternforge_docops._internal.allure import curate_results, generate_reports


def build_html(
    root: Path,
    *,
    docs: Path | None = None,
    output: Path | None = None,
) -> Path:
    """Build strict HTML documentation without executing project tests."""
    docs_root = docs or root / "docs"
    output_root = output or docs_root / "_build" / "html"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "sphinx",
            "-E",
            "-W",
            "--keep-going",
            "-D",
            "plot_gallery=0",
            "-b",
            "html",
            str(docs_root),
            str(output_root),
        ],
        cwd=root,
        check=True,
    )
    return output_root


def build_portal(
    root: Path,
    *,
    allure_results: Path,
    docs: Path | None = None,
    output: Path | None = None,
) -> Path:
    """Build docs plus Allure perspectives from pre-existing evidence inputs."""
    output_root = build_html(root, docs=docs, output=output)
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
