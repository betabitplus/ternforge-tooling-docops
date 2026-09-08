"""Allure 3 forensic report generation using the upstream Awesome reporter."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404 - Allure 3 is an external Node CLI with no Python API.
from pathlib import Path

_ALLURE_VERSION = "3.16.0"


def generate_report(*, curated_results: Path, output: Path) -> Path:
    """Generate the pinned Allure forensic execution browser."""
    npx = shutil.which("npx")
    if npx is None:
        message = "npx is required to generate the Allure 3 report"
        raise RuntimeError(message)
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(output, ignore_errors=True)
    subprocess.run(  # nosec B603 - absolute npx path, fixed argv, shell remains disabled.
        [
            npx,
            "--yes",
            f"allure@{_ALLURE_VERSION}",
            "awesome",
            str(curated_results),
            "--output",
            str(output),
            "--report-name",
            "All test results",
            "--group-by",
            "layer,parentSuite,suite",
            "--single-file",
        ],
        check=True,
    )
    report = output / "index.html"
    if not report.is_file():
        message = f"Allure did not produce {report}"
        raise RuntimeError(message)
    return report
