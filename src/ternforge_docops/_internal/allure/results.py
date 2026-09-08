"""Shared current-result selection for Allure-backed DocOps views."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

type ExecutionKey = tuple[str, int, str]


@dataclass(frozen=True)
class CurrentAllureResult:
    """One latest retained Allure result and its source file."""

    source_path: Path
    data: dict[str, Any]


def labels(result: dict[str, Any], name: str) -> tuple[str, ...]:
    """Return ordered values for one Allure label name."""
    values = result.get("labels")
    if not isinstance(values, list):
        return ()
    return tuple(
        str(label.get("value"))
        for label in values
        if isinstance(label, dict) and label.get("name") == name and label.get("value")
    )


def execution_key(result: dict[str, Any]) -> ExecutionKey:
    """Return the execution fields preserved by the generated Allure report."""
    return (
        str(result.get("fullName") or ""),
        int(result.get("start") or 0),
        str(result.get("name") or ""),
    )


def _identity(result: dict[str, Any], result_path: Path) -> str:
    """Return the stable identity used to select the latest retained execution."""
    return str(
        result.get("historyId")
        or result.get("uuid")
        or result.get("testCaseId")
        or result_path.name
    )


def _ordering(result: dict[str, Any], result_path: Path) -> tuple[int, int, str]:
    """Order repeated executions by captured finish/start times and file name."""
    return (
        int(result.get("stop") or result.get("start") or 0),
        int(result.get("start") or 0),
        result_path.name,
    )


def _read_result(result_path: Path) -> dict[str, Any] | None:
    """Read one Allure result defensively, ignoring malformed files."""
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return result if isinstance(result, dict) else None


def current_results(raw_results: Path) -> tuple[CurrentAllureResult, ...]:
    """Return exactly one latest retained execution for every Allure identity."""
    current: dict[
        str,
        tuple[tuple[int, int, str], CurrentAllureResult],
    ] = {}
    for result_path in sorted(raw_results.glob("*-result.json")):
        result = _read_result(result_path)
        if result is None:
            continue
        identity = _identity(result, result_path)
        ordering = _ordering(result, result_path)
        previous = current.get(identity)
        if previous is None or ordering > previous[0]:
            current[identity] = (
                ordering,
                CurrentAllureResult(source_path=result_path, data=result),
            )
    return tuple(value[1] for value in current.values())
