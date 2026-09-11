"""Structured runtime evidence used by verification narratives and assurance views."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ternforge_docops._internal.allure.results import current_results

VERIFICATION_OBSERVATION_MEDIA_TYPE = (
    "application/vnd.ternforge.verification-observation+json"
)


@dataclass(frozen=True)
class VerificationEvidencePaths:
    """Standard retained verification artifacts consumed by DocOps."""

    junit: Path | None = None
    allure_results: Path | None = None
    coverage: Path | None = None


@dataclass(frozen=True)
class VerificationObservation:
    """One raw verification fact emitted during test execution."""

    name: str
    kind: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class VerificationRuntimeEvidence:
    """All structured runtime facts retained for one pytest nodeid."""

    nodeid: str
    observations: tuple[VerificationObservation, ...]

    @property
    def execution(self) -> VerificationObservation | None:
        """Return the standard test-execution observation when present."""
        return next(
            (item for item in self.observations if item.kind == "test-execution"),
            None,
        )

    @property
    def fixtures(self) -> tuple[str, ...]:
        """Return runtime fixture names captured by py-testkit."""
        execution = self.execution
        if execution is None:
            return ()
        raw = execution.payload.get("fixtures")
        if not isinstance(raw, list):
            return ()
        return tuple(str(value) for value in raw if str(value).strip())

    @property
    def markers(self) -> tuple[str, ...]:
        """Return runtime mechanism markers captured by py-testkit."""
        execution = self.execution
        if execution is None:
            return ()
        raw = execution.payload.get("markers")
        if not isinstance(raw, list):
            return ()
        return tuple(str(value) for value in raw if str(value).strip())

    @property
    def source_path(self) -> str:
        """Return the pytest source path captured during execution."""
        execution = self.execution
        if execution is None:
            return ""
        return str(execution.payload.get("path") or "")


@dataclass(frozen=True)
class ExternalSubstituteObservation:
    """One explicitly captured replacement for an external boundary."""

    producer: str
    boundary: str
    mode: str
    transport: str
    target: str


def _external_substitute(
    observation: VerificationObservation,
) -> ExternalSubstituteObservation | None:
    """Normalize one explicit external-substitute observation."""
    if observation.kind != "external-substitute":
        return None
    payload = observation.payload
    producer = str(payload.get("producer") or "").strip()
    if not producer:
        return None
    return ExternalSubstituteObservation(
        producer=producer,
        boundary=str(payload.get("boundary") or "").strip(),
        mode=str(payload.get("mode") or "").strip(),
        transport=str(payload.get("transport") or "").strip(),
        target=str(payload.get("target") or "").strip(),
    )


def external_substitutes(
    runtime: VerificationRuntimeEvidence | None,
) -> tuple[ExternalSubstituteObservation, ...]:
    """Return explicitly captured external substitutions for one execution."""
    if runtime is None:
        return ()
    values = tuple(
        item
        for observation in runtime.observations
        if (item := _external_substitute(observation)) is not None
    )
    return tuple(dict.fromkeys(values))


def _nested_attachments(node: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    """Return root and step attachments from one Allure result fragment."""
    values: list[dict[str, Any]] = []
    raw_attachments = node.get("attachments")
    if isinstance(raw_attachments, list):
        values.extend(item for item in raw_attachments if isinstance(item, dict))
    raw_steps = node.get("steps")
    if isinstance(raw_steps, list):
        for step in raw_steps:
            if isinstance(step, dict):
                values.extend(_nested_attachments(step))
    return tuple(values)


def _observation_payload(
    raw_results: Path,
    attachment: dict[str, Any],
) -> dict[str, Any] | None:
    """Read and validate the envelope of one py-testkit observation attachment."""
    if attachment.get("type") != VERIFICATION_OBSERVATION_MEDIA_TYPE:
        return None
    source = attachment.get("source")
    if not isinstance(source, str) or not source:
        return None
    try:
        payload = json.loads((raw_results / source).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return (
        payload
        if isinstance(payload, dict) and payload.get("schema_version") == 1
        else None
    )


def _read_observation(
    raw_results: Path,
    attachment: dict[str, Any],
) -> VerificationObservation | None:
    """Read one py-testkit observation attachment defensively."""
    payload = _observation_payload(raw_results, attachment)
    if payload is None:
        return None
    kind = payload.get("kind")
    data = payload.get("payload")
    if not isinstance(kind, str) or not kind.strip() or not isinstance(data, dict):
        return None
    return VerificationObservation(
        name=str(attachment.get("name") or kind),
        kind=kind.strip(),
        payload=data,
    )


def runtime_evidence_for_result(
    raw_results: Path,
    result: dict[str, Any],
) -> VerificationRuntimeEvidence | None:
    """Return structured runtime facts attached to one concrete Allure result."""
    observations = tuple(
        observation
        for attachment in _nested_attachments(result)
        if (observation := _read_observation(raw_results, attachment)) is not None
    )
    execution = next(
        (item for item in observations if item.kind == "test-execution"),
        None,
    )
    if execution is None:
        return None
    nodeid = str(execution.payload.get("nodeid") or "").strip()
    if not nodeid:
        return None
    return VerificationRuntimeEvidence(nodeid=nodeid, observations=observations)


def load_runtime_evidence(
    raw_results: Path | None,
) -> dict[str, VerificationRuntimeEvidence]:
    """Load structured observations grouped by the pytest nodeid that emitted them."""
    if raw_results is None or not raw_results.is_dir():
        return {}
    grouped: dict[str, VerificationRuntimeEvidence] = {}
    for current in current_results(raw_results):
        evidence = runtime_evidence_for_result(raw_results, current.data)
        if evidence is not None:
            grouped[evidence.nodeid] = evidence
    return grouped


def inferred_nodeid(classname: str, name: str) -> str:
    """Return the conventional pytest nodeid for a module-level JUnit testcase."""
    path = classname.replace(".", "/")
    return f"{path}.py::{name}"


def resolve_runtime_evidence(
    evidence: dict[str, VerificationRuntimeEvidence],
    *,
    classname: str,
    name: str,
) -> VerificationRuntimeEvidence | None:
    """Resolve runtime evidence for a JUnit testcase without guessing across modules."""
    candidate = inferred_nodeid(classname, name)
    if candidate in evidence:
        return evidence[candidate]
    path = f"{classname.replace('.', '/')}.py"
    matches = [
        item
        for item in evidence.values()
        if item.source_path == path and item.nodeid.endswith(f"::{name}")
    ]
    return matches[0] if len(matches) == 1 else None
