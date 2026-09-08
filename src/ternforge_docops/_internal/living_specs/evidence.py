"""Current BDD evidence parsing for native Living Specifications."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

from ternforge_docops._internal.living_specs.models import (
    LivingAttachment,
    LivingExample,
    LivingStep,
)

_SPECIFICATION_RE = re.compile(
    r"(?:^|\n)Specification:\s*(?P<path>[^:\n]+):(?P<line>\d+)\s*$"
)
_STATUS_ORDER = {"failed": 0, "broken": 1, "skipped": 2, "unknown": 3, "passed": 4}


def _labels(result: dict[str, Any], name: str) -> tuple[str, ...]:
    """Return ordered values for one Allure label name."""
    labels = result.get("labels")
    if not isinstance(labels, list):
        return ()
    return tuple(
        str(label.get("value"))
        for label in labels
        if isinstance(label, dict) and label.get("name") == name and label.get("value")
    )


def _one_label(result: dict[str, Any], name: str, fallback: str) -> str:
    """Return the first value for one Allure label or a fallback."""
    values = _labels(result, name)
    return values[0] if values else fallback


def _status(result: dict[str, Any]) -> str:
    """Normalize one Allure status into the supported presentation vocabulary."""
    value = str(result.get("status") or "unknown").lower()
    return value if value in _STATUS_ORDER else "unknown"


def _bdd_example_parameters(result: dict[str, Any]) -> dict[Any, Any] | None:
    """Parse pytest-bdd example parameters from retained Allure metadata."""
    parameters = result.get("parameters")
    if not isinstance(parameters, list):
        return None
    for parameter in parameters:
        if not isinstance(parameter, dict):
            continue
        if parameter.get("name") != "_pytest_bdd_example":
            continue
        try:
            parsed = ast.literal_eval(str(parameter.get("value")))
        except (SyntaxError, ValueError):
            continue
        if isinstance(parsed, dict) and parsed:
            return parsed
    return None


def _example_name(result: dict[str, Any], story: str) -> str:
    """Derive a concise example label for scenario-outline tabs."""
    parsed = _bdd_example_parameters(result)
    if parsed:
        if len(parsed) == 1:
            return str(next(iter(parsed.values())))
        return ", ".join(f"{key}={value}" for key, value in parsed.items())
    result_name = str(result.get("name") or "")
    return result_name if result_name and result_name != story else "Scenario"


def _description_and_specification(
    result: dict[str, Any],
) -> tuple[str, str, int | None]:
    """Split authored feature narrative from the reported Gherkin source location."""
    description = str(result.get("description") or "").strip()
    match = _SPECIFICATION_RE.search(description)
    if match is None:
        return description, "", None
    narrative = description[: match.start()].strip()
    return narrative, match.group("path").strip(), int(match.group("line"))


def _resolve_source(root: Path, reported: str) -> tuple[str, bool]:
    """Resolve a reported Gherkin source path against supported consumer layouts."""
    if not reported:
        return "", False
    reported_path = Path(reported)
    candidates = (reported_path, Path("features") / reported_path)
    for candidate in candidates:
        if (root / candidate).is_file():
            return candidate.as_posix(), True
    return reported_path.as_posix(), False


def _attachment(raw_results: Path, value: dict[str, Any]) -> LivingAttachment:
    """Normalize one retained Allure attachment and validate its local source."""
    source_name = str(value.get("source") or "")
    safe_name = (
        source_name if source_name and Path(source_name).name == source_name else None
    )
    source = raw_results / safe_name if safe_name else None
    if source is not None and not source.is_file():
        source = None
    return LivingAttachment(
        name=str(value.get("name") or "Evidence"),
        media_type=str(value.get("type") or "application/octet-stream"),
        source=source,
        output_name=safe_name if source is not None else None,
    )


def _attachments(
    raw_results: Path, value: dict[str, Any]
) -> tuple[LivingAttachment, ...]:
    """Normalize the attachment list carried by one Allure result or step."""
    values = value.get("attachments")
    if not isinstance(values, list):
        return ()
    return tuple(
        _attachment(raw_results, attachment)
        for attachment in values
        if isinstance(attachment, dict)
    )


def _steps(raw_results: Path, result: dict[str, Any]) -> tuple[LivingStep, ...]:
    """Normalize executed Given/When/Then steps and their retained evidence."""
    values = result.get("steps")
    if not isinstance(values, list):
        return ()
    return tuple(
        LivingStep(
            name=str(step.get("name") or "Step"),
            status=str(step.get("status") or "unknown"),
            attachments=_attachments(raw_results, step),
        )
        for step in values
        if isinstance(step, dict)
    )


def _read_result(result_path: Path) -> dict[str, Any] | None:
    """Read one Allure result defensively, ignoring malformed or unreadable files."""
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return result if isinstance(result, dict) else None


def _result_identity(result: dict[str, Any], result_path: Path) -> str:
    """Return the stable execution identity used for current-result selection."""
    return str(
        result.get("historyId")
        or result.get("uuid")
        or result.get("testCaseId")
        or result_path.name
    )


def _result_ordering(result: dict[str, Any], result_path: Path) -> tuple[int, int, str]:
    """Return a deterministic ordering key for repeated executions."""
    return (
        int(result.get("stop") or result.get("start") or 0),
        int(result.get("start") or 0),
        result_path.name,
    )


def _current_bdd_results(raw_results: Path) -> tuple[dict[str, Any], ...]:
    """Select only the latest retained execution for each BDD example identity."""
    current: dict[str, tuple[tuple[int, int, str], dict[str, Any]]] = {}
    for result_path in sorted(raw_results.glob("*-result.json")):
        result = _read_result(result_path)
        if result is None or "bdd" not in _labels(result, "layer"):
            continue
        identity = _result_identity(result, result_path)
        ordering = _result_ordering(result, result_path)
        previous = current.get(identity)
        if previous is None or ordering > previous[0]:
            current[identity] = (ordering, result)
    return tuple(value[1] for value in current.values())


def _duration_ms(result: dict[str, Any]) -> int | None:
    """Compute captured execution duration when both timestamps are available."""
    start = result.get("start")
    stop = result.get("stop")
    if not isinstance(start, int | float) or not isinstance(stop, int | float):
        return None
    return max(0, int(stop) - int(start))


def _status_details(result: dict[str, Any]) -> tuple[str, str]:
    """Extract failure message and trace from Allure status details."""
    details = result.get("statusDetails")
    if not isinstance(details, dict):
        return "", ""
    return str(details.get("message") or ""), str(details.get("trace") or "")


def _example(root: Path, raw_results: Path, result: dict[str, Any]) -> LivingExample:
    """Normalize one current Allure BDD result into the Living Specs model."""
    feature = _one_label(result, "feature", "Executable behavior")
    rule = _one_label(result, "rule", "Behavior rule")
    story = _one_label(result, "story", str(result.get("name") or "Scenario"))
    description, reported_source, source_line = _description_and_specification(result)
    source_path, source_exists = _resolve_source(root, reported_source)
    status_message, status_trace = _status_details(result)
    return LivingExample(
        name=_example_name(result, story),
        status=_status(result),
        epic=_one_label(result, "epic", "Executable behavior"),
        feature=feature,
        feature_description=description,
        rule=rule,
        story=story,
        requirements=tuple(dict.fromkeys(_labels(result, "requirement"))),
        tags=tuple(dict.fromkeys(_labels(result, "tag"))),
        steps=_steps(raw_results, result),
        attachments=_attachments(raw_results, result),
        duration_ms=_duration_ms(result),
        full_name=str(result.get("fullName") or ""),
        source_path=source_path,
        source_line=source_line,
        source_exists=source_exists,
        status_message=status_message,
        status_trace=status_trace,
    )


def load_examples(root: Path, raw_results: Path) -> tuple[LivingExample, ...]:
    """Load the latest BDD executions and normalize them for presentation."""
    examples = [
        _example(root, raw_results, result)
        for result in _current_bdd_results(raw_results)
    ]
    return tuple(
        sorted(
            examples,
            key=lambda item: (
                item.epic.casefold(),
                item.feature.casefold(),
                item.source_line or 0,
                item.rule.casefold(),
                item.story.casefold(),
                item.name.casefold(),
            ),
        )
    )
