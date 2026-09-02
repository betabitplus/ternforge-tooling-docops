"""Allure 3 report generation using the upstream Awesome reporter."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

_ALLURE_VERSION = "3.16.0"


def _generate_report(
    source: Path,
    *,
    npx: str,
    output: Path,
    group_by: str,
    report_name: str,
) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(output, ignore_errors=True)
    subprocess.run(
        [
            npx,
            "--yes",
            f"allure@{_ALLURE_VERSION}",
            "awesome",
            str(source),
            "--output",
            str(output),
            "--report-name",
            report_name,
            "--group-by",
            group_by,
            "--single-file",
        ],
        check=True,
    )
    report = output / "index.html"
    if not report.is_file():
        message = f"Allure did not produce {report}"
        raise RuntimeError(message)
    return report


def generate_reports(
    *,
    curated_results: Path,
    bdd_results: Path,
    output_root: Path,
) -> dict[str, Path]:
    """Generate the standard DocOps Allure perspectives."""
    npx = shutil.which("npx")
    if npx is None:
        message = "npx is required to generate Allure 3 reports"
        raise RuntimeError(message)
    return {
        "bdd": _generate_report(
            bdd_results,
            npx=npx,
            output=output_root / "bdd",
            group_by="epic,feature,rule",
            report_name="Executable specifications",
        ),
        "requirements": _generate_report(
            curated_results,
            npx=npx,
            output=output_root / "requirements",
            group_by="requirement_view,layer",
            report_name="Verification by requirement",
        ),
        "all": _generate_report(
            curated_results,
            npx=npx,
            output=output_root / "all",
            group_by="layer,parentSuite,suite",
            report_name="All test results",
        ),
    }
