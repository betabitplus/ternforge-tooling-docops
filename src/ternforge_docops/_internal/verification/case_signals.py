"""Objective runtime/source signals used by non-BDD boundary semantics."""

from __future__ import annotations

from dataclasses import dataclass

from ternforge_docops._internal.verification.assurance import (
    RuntimeAssuranceFacts,
    runtime_assurance_facts,
)
from ternforge_docops._internal.verification.coverage_evidence import CoverageFootprint
from ternforge_docops._internal.verification.evidence import VerificationRuntimeEvidence
from ternforge_docops._internal.verification.source_analysis import (
    module_title as _module_title,
    subject as _subject,
    test_double_names as _test_double_names,
)


@dataclass(frozen=True)
class CaseBoundaryInput:
    """Exact testcase facts used to infer the verification boundary."""

    kind: str
    source_path: str
    code: str
    exercises: tuple[str, ...]
    checks: tuple[str, ...]
    generated_inputs: tuple[str, ...]
    runtime: VerificationRuntimeEvidence | None
    coverage: CoverageFootprint | None


@dataclass(frozen=True)
class BoundarySignals:
    """Objective execution signals recovered from one testcase body."""

    scripted_http: bool
    vcr: bool
    replay: bool
    direct_external: bool
    hypothesis: bool
    temporary_filesystem: bool
    patched_runtime: bool
    subprocess: bool
    doubles: tuple[str, ...]
    module: str
    subject: str
    runtime_modules: tuple[str, ...]
    assurance: RuntimeAssuranceFacts | None


def _runtime_or_source(
    *,
    has_runtime: bool,
    captured: bool,
    source_fallback: bool,
) -> bool:
    """Prefer a captured boolean signal over source-derived fallback."""
    return captured if has_runtime else source_fallback


def _boundary_doubles(
    facts: RuntimeAssuranceFacts | None,
    code: str,
    *,
    has_runtime: bool,
) -> tuple[str, ...]:
    """Return captured substitute producers or source-derived fallback names."""
    if facts is not None and facts.substitutes:
        return tuple(dict.fromkeys(item.producer for item in facts.substitutes))
    return () if has_runtime else _test_double_names(code)


def _captured_mechanism(
    facts: RuntimeAssuranceFacts | None,
    *,
    has_runtime: bool,
) -> str:
    """Return the captured primary mechanism only when runtime evidence exists."""
    return facts.mechanism if facts is not None and has_runtime else ""


def _captured_interaction(
    facts: RuntimeAssuranceFacts | None,
    relation: str,
) -> bool:
    """Return whether runtime evidence captured one boundary relation."""
    if facts is None:
        return False
    return any(item.interaction.casefold() == relation for item in facts.interactions)


def _captured_marker(
    facts: RuntimeAssuranceFacts | None,
    marker: str,
) -> bool:
    """Return whether runtime evidence captured one pytest marker."""
    if facts is None:
        return False
    return any(value.casefold() == marker for value in facts.markers)


def _captured_state(
    facts: RuntimeAssuranceFacts | None,
    field: str,
    expected: str,
) -> bool:
    """Return whether one normalized runtime envelope field has an expected value."""
    return facts is not None and getattr(facts, field) == expected


def _source_temporary_filesystem(code: str) -> bool:
    """Return whether source fallback visibly uses a temporary filesystem fixture."""
    return "tmp_path" in code or "TemporaryDirectory" in code


def _source_subprocess(code: str) -> bool:
    """Return whether source fallback visibly invokes a subprocess API."""
    return "subprocess." in code or "Popen(" in code


def boundary_signals(value: CaseBoundaryInput) -> BoundarySignals:
    """Prefer shared runtime facts and use source inspection only as fallback."""
    facts = runtime_assurance_facts(value.runtime, value.coverage)
    has_runtime = value.runtime is not None
    mechanism = _captured_mechanism(facts, has_runtime=has_runtime)
    return BoundarySignals(
        scripted_http=_runtime_or_source(
            has_runtime=has_runtime,
            captured=mechanism == "scripted-http",
            source_fallback="ScriptedHTTPServer" in value.code,
        ),
        vcr=mechanism == "vcr",
        replay=mechanism == "vcr" or _captured_interaction(facts, "replay"),
        direct_external=_captured_interaction(facts, "direct"),
        hypothesis=_captured_marker(facts, "hypothesis"),
        temporary_filesystem=_runtime_or_source(
            has_runtime=has_runtime,
            captured=_captured_state(facts, "filesystem", "temporary"),
            source_fallback=_source_temporary_filesystem(value.code),
        ),
        patched_runtime=_runtime_or_source(
            has_runtime=has_runtime,
            captured=mechanism == "patched-runtime",
            source_fallback="monkeypatch" in value.code,
        ),
        subprocess=_runtime_or_source(
            has_runtime=has_runtime,
            captured=_captured_state(facts, "process", "subprocess"),
            source_fallback=_source_subprocess(value.code),
        ),
        doubles=_boundary_doubles(
            facts,
            value.code,
            has_runtime=has_runtime,
        ),
        module=_module_title(value.source_path) if value.source_path else "Component",
        subject=_subject(value.exercises),
        runtime_modules=facts.modules if facts is not None else (),
        assurance=facts,
    )
