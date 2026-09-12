"""Current BDD evidence parsing for native Living Specifications."""

from __future__ import annotations

import ast
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ternforge_docops._internal.allure.results import (
    ExecutionKey,
    current_results,
    execution_key,
    labels,
)
from ternforge_docops._internal.living_specs.boundary import infer_boundary
from ternforge_docops._internal.living_specs.execution_evidence import (
    INTERNAL_ATTACHMENT_TYPES,
    contracts as _contracts,
    implementation as _implementation,
)
from ternforge_docops._internal.living_specs.models import (
    LivingAttachment,
    LivingExample,
    LivingStep,
)
from ternforge_docops._internal.verification.coverage_evidence import (
    CoverageFootprint,
    load_coverage_footprints,
)
from ternforge_docops._internal.verification.evidence import runtime_evidence_for_result

_SPECIFICATION_RE = re.compile(
    r"(?:^|\n)Specification:\s*(?P<path>[^:\n]+):(?P<line>\d+)\s*$"
)
_STATUS_ORDER = {"failed": 0, "broken": 1, "skipped": 2, "unknown": 3, "passed": 4}


def _one_label(result: dict[str, Any], name: str, fallback: str) -> str:
    """Return the first value for one Allure label or a fallback."""
    values = labels(result, name)
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
    """Normalize user-facing attachments carried by one Allure result or step."""
    values = value.get("attachments")
    if not isinstance(values, list):
        return ()
    return tuple(
        _attachment(raw_results, attachment)
        for attachment in values
        if isinstance(attachment, dict)
        and str(attachment.get("type") or "") not in INTERNAL_ATTACHMENT_TYPES
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
            implementation=_implementation(raw_results, step),
            contracts=_contracts(raw_results, step),
        )
        for step in values
        if isinstance(step, dict)
    )


def _duration_ms(result: dict[str, Any]) -> int | None:
    """Compute captured execution duration when both timestamps are available."""
    start = result.get("start")
    stop = result.get("stop")
    if not isinstance(start, int | float) or not isinstance(stop, int | float):
        return None
    return max(0, int(stop) - int(start))


def _started_ms(result: dict[str, Any]) -> int | None:
    """Return the captured start timestamp when available."""
    start = result.get("start")
    return int(start) if isinstance(start, int | float) else None


def _status_details(result: dict[str, Any]) -> tuple[str, str]:
    """Extract failure message and trace from Allure status details."""
    details = result.get("statusDetails")
    if not isinstance(details, dict):
        return "", ""
    return str(details.get("message") or ""), str(details.get("trace") or "")


def _example(
    root: Path,
    raw_results: Path,
    result: dict[str, Any],
    result_links: Mapping[ExecutionKey, str],
    coverage_footprints: Mapping[str, CoverageFootprint],
) -> LivingExample:
    """Normalize one current Allure BDD result into the Living Specs model."""
    feature = _one_label(result, "feature", "Executable behavior")
    rule = _one_label(result, "rule", "Behavior rule")
    story = _one_label(result, "story", str(result.get("name") or "Scenario"))
    description, reported_source, source_line = _description_and_specification(result)
    source_path, source_exists = _resolve_source(root, reported_source)
    status_message, status_trace = _status_details(result)
    tags = tuple(dict.fromkeys(labels(result, "tag")))
    steps = _steps(raw_results, result)
    runtime = runtime_evidence_for_result(raw_results, result)
    coverage = coverage_footprints.get(runtime.nodeid) if runtime is not None else None
    return LivingExample(
        name=_example_name(result, story),
        status=_status(result),
        epic=_one_label(result, "epic", "Executable behavior"),
        feature=feature,
        feature_description=description,
        rule=rule,
        story=story,
        requirements=tuple(dict.fromkeys(labels(result, "requirement"))),
        tags=tags,
        steps=steps,
        attachments=_attachments(raw_results, result),
        duration_ms=_duration_ms(result),
        started_ms=_started_ms(result),
        full_name=str(result.get("fullName") or ""),
        nodeid="" if runtime is None else runtime.nodeid,
        allure_url=result_links.get(execution_key(result), ""),
        source_path=source_path,
        source_line=source_line,
        source_exists=source_exists,
        status_message=status_message,
        status_trace=status_trace,
        boundary=infer_boundary(
            tags=tags,
            steps=steps,
            runtime=runtime,
            coverage=coverage,
        ),
    )


def load_examples(
    root: Path,
    raw_results: Path,
    *,
    result_links: Mapping[ExecutionKey, str] | None = None,
    coverage: Path | None = None,
) -> tuple[LivingExample, ...]:
    """Load the exact current BDD executions shared with the forensic Allure view."""
    links = result_links or {}
    coverage_footprints = load_coverage_footprints(coverage)
    examples = [
        _example(root, raw_results, current.data, links, coverage_footprints)
        for current in current_results(raw_results)
        if "bdd" in labels(current.data, "layer")
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
