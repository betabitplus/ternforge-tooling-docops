"""Allure result curation for the current forensic execution view."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


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


def _identity(result: dict[str, Any], result_path: Path) -> str:
    """Return the stable Allure identity used to select the latest execution."""
    return str(
        result.get("historyId")
        or result.get("uuid")
        or result.get("testCaseId")
        or result_path.name
    )


def _ordering(result: dict[str, Any], result_path: Path) -> tuple[int, int, str]:
    """Order repeated executions by their captured finish/start times."""
    return (
        int(result.get("stop") or result.get("start") or 0),
        int(result.get("start") or 0),
        result_path.name,
    )


def _current_results(raw_results: Path) -> tuple[tuple[Path, dict[str, Any]], ...]:
    """Return only the latest Allure result for each execution identity."""
    current: dict[str, tuple[tuple[int, int, str], Path, dict[str, Any]]] = {}
    for result_path in sorted(raw_results.glob("*-result.json")):
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(result, dict):
            continue
        identity = _identity(result, result_path)
        ordering = _ordering(result, result_path)
        previous = current.get(identity)
        if previous is None or ordering > previous[0]:
            current[identity] = (ordering, result_path, result)
    return tuple((value[1], value[2]) for value in current.values())


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
    for result_path, result in _current_results(raw_results):
        _copy_result(
            result_path,
            result,
            raw_results=raw_results,
            destination=curated_results,
        )
