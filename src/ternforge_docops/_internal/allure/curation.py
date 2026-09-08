"""Allure result curation for the current forensic execution view."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from ternforge_docops._internal.allure.results import current_results


def _attachment_sources(result: dict[str, object]) -> set[str]:
    """Collect attachments referenced by a result and its nested steps."""
    sources: set[str] = set()
    pending: list[dict[str, object]] = [result]
    while pending:
        value = pending.pop()
        attachments = value.get("attachments")
        if isinstance(attachments, list):
            for attachment in attachments:
                if isinstance(attachment, dict) and attachment.get("source"):
                    sources.add(str(attachment["source"]))
        steps = value.get("steps")
        if isinstance(steps, list):
            pending.extend(step for step in steps if isinstance(step, dict))
    return sources


def _copy_result(
    result_path: Path,
    result: dict[str, object],
    *,
    raw_results: Path,
    destination: Path,
) -> None:
    """Write one current Allure result and only its referenced attachments."""
    destination.mkdir(parents=True, exist_ok=True)
    (destination / result_path.name).write_text(
        json.dumps(result, ensure_ascii=False),
        encoding="utf-8",
    )
    for source in _attachment_sources(result):
        attachment = raw_results / source
        if attachment.is_file():
            shutil.copy2(attachment, destination / source)


def curate_results(raw_results: Path, *, curated_results: Path) -> None:
    """Create a fixture-free, current-only Allure result set for forensic browsing."""
    shutil.rmtree(curated_results, ignore_errors=True)
    curated_results.mkdir(parents=True)
    for current in current_results(raw_results):
        _copy_result(
            current.source_path,
            current.data,
            raw_results=raw_results,
            destination=curated_results,
        )
