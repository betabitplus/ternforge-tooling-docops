"""Allure 3 forensic report generation using the upstream Awesome reporter."""

from __future__ import annotations

import base64
import json
import re
import shutil
import subprocess  # nosec B404 - Allure 3 is an external Node CLI with no Python API.
from pathlib import Path
from typing import Any

from ternforge_docops._internal.allure.results import ExecutionKey, execution_key

_ALLURE_VERSION = "3.16.0"
_RESULT_DATA_RE = re.compile(
    r'"data/test-results/(?P<id>[0-9a-f]+)\.json","(?P<payload>[A-Za-z0-9+/=]+)"'
)


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


def _decoded_result(payload: str) -> dict[str, Any] | None:
    """Decode one embedded Allure single-file test-result payload."""
    try:
        value = json.loads(base64.b64decode(payload, validate=True))
    except (ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def extract_result_links(report: Path) -> dict[ExecutionKey, str]:
    """Map current executions to direct links in the pinned Allure single-file UI."""
    html = report.read_text(encoding="utf-8", errors="replace")
    links: dict[ExecutionKey, str] = {}
    for match in _RESULT_DATA_RE.finditer(html):
        result = _decoded_result(match.group("payload"))
        if result is None:
            continue
        links[execution_key(result)] = f"test-results/index.html#{match.group('id')}"
    return links
