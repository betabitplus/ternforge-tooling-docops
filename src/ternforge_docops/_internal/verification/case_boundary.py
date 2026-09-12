"""Boundary semantics for source-enriched non-BDD verification narratives."""

from __future__ import annotations

from dataclasses import dataclass

from ternforge_docops._internal.verification.assurance import (
    RuntimeAssuranceFacts,
    VerificationBoundary,
    runtime_assurance_facts,
)
from ternforge_docops._internal.verification.coverage_evidence import CoverageFootprint
from ternforge_docops._internal.verification.evidence import VerificationRuntimeEvidence
from ternforge_docops._internal.verification.source_analysis import (
    module_title as _module_title,
    observed_proof as _observed_proof,
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
class _BoundarySignals:
    """Objective execution signals recovered from one testcase body."""

    scripted_http: bool
    vcr: bool
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
    mechanism: str,
    code: str,
    *,
    has_runtime: bool,
) -> tuple[str, ...]:
    """Return captured substitute producers or source-derived fallback names."""
    if mechanism == "external-double" and facts is not None:
        return tuple(dict.fromkeys(item.producer for item in facts.substitutes))
    return () if has_runtime else _test_double_names(code)


def _boundary_signals(value: CaseBoundaryInput) -> _BoundarySignals:
    """Prefer shared runtime facts and use source inspection only as fallback."""
    facts = runtime_assurance_facts(value.runtime, value.coverage)
    has_runtime = value.runtime is not None
    mechanism = facts.mechanism if facts is not None and has_runtime else ""
    temporary = facts is not None and facts.filesystem == "temporary"
    subprocess = facts is not None and facts.process == "subprocess"
    return _BoundarySignals(
        scripted_http=_runtime_or_source(
            has_runtime=has_runtime,
            captured=mechanism == "scripted-http",
            source_fallback="ScriptedHTTPServer" in value.code,
        ),
        vcr=mechanism == "vcr",
        temporary_filesystem=_runtime_or_source(
            has_runtime=has_runtime,
            captured=temporary,
            source_fallback=(
                "tmp_path" in value.code or "TemporaryDirectory" in value.code
            ),
        ),
        patched_runtime=_runtime_or_source(
            has_runtime=has_runtime,
            captured=mechanism == "patched-runtime",
            source_fallback="monkeypatch" in value.code,
        ),
        subprocess=_runtime_or_source(
            has_runtime=has_runtime,
            captured=subprocess,
            source_fallback=("subprocess." in value.code or "Popen(" in value.code),
        ),
        doubles=_boundary_doubles(
            facts,
            mechanism,
            value.code,
            has_runtime=has_runtime,
        ),
        module=_module_title(value.source_path) if value.source_path else "Component",
        subject=_subject(value.exercises),
        runtime_modules=facts.modules if facts is not None else (),
        assurance=facts,
    )


def _network_envelope(
    kind: str,
    signals: _BoundarySignals,
    facts: RuntimeAssuranceFacts | None,
) -> str:
    """Describe the observed network mechanism."""
    if facts is not None and facts.network:
        return facts.network
    if signals.scripted_http:
        return "localhost HTTP"
    if signals.vcr:
        return "recorded HTTP replay"
    return "not explicit" if kind in {"integration", "e2e"} else "not exercised"


def _external_envelope(
    kind: str,
    signals: _BoundarySignals,
    facts: RuntimeAssuranceFacts | None,
) -> str:
    """Describe observed external-system participation."""
    if facts is not None and facts.external:
        return facts.external
    if signals.scripted_http:
        return "scripted provider"
    if signals.vcr:
        return "recorded provider interaction"
    if signals.doubles:
        return f"{', '.join(signals.doubles)} test double"
    return "not explicit" if kind in {"integration", "e2e"} else "not exercised"


def _execution_envelope(
    value: CaseBoundaryInput,
    signals: _BoundarySignals,
) -> tuple[str, str, str, str]:
    """Describe process, network, filesystem, and external-system participation."""
    facts = signals.assurance if value.runtime is not None else None
    process = (
        facts.process
        if facts is not None
        else ("subprocess" if signals.subprocess else "in-process")
    )
    filesystem = (
        facts.filesystem
        if facts is not None
        else ("temporary" if signals.temporary_filesystem else "not exercised")
    )
    return (
        process,
        _network_envelope(value.kind, signals, facts),
        filesystem,
        _external_envelope(value.kind, signals, facts),
    )


def _transport_substitute(signals: _BoundarySignals) -> str:
    """Return the primary transport substitute, if one was observed."""
    if signals.scripted_http:
        return "live provider/service → local ScriptedHTTPServer"
    if signals.vcr:
        return "live HTTP interaction → retained VCR replay"
    return ""


def _external_substitute_text(signals: _BoundarySignals) -> tuple[str, ...]:
    """Return captured external SDK/provider substitutions."""
    facts = signals.assurance
    if facts is not None and facts.mechanism == "external-double":
        return tuple(
            f"{item.target or 'external SDK/provider'} → {item.producer}"
            for item in facts.substitutes
        )
    if signals.doubles:
        return (f"real SDK/provider client → {', '.join(signals.doubles)}",)
    return ()


def _substitute(signals: _BoundarySignals) -> str:
    """Describe explicit substitutions, preferring their captured target semantics."""
    values = [
        _transport_substitute(signals),
        *_external_substitute_text(signals),
        (
            "host/persistent path → isolated temporary path"
            if signals.temporary_filesystem
            else ""
        ),
        (
            "host environment/runtime state → pytest monkeypatch"
            if signals.patched_runtime
            else ""
        ),
    ]
    rendered = "; ".join(dict.fromkeys(value for value in values if value))
    return rendered or "No explicit substitute is visible in this testcase."


def _observed_runtime_path(signals: _BoundarySignals) -> str:
    """Return the actual production modules executed by this test when available."""
    return " → ".join(signals.runtime_modules)


def _unit_scope(signals: _BoundarySignals) -> tuple[str, str, str]:
    """Describe the semantic boundary of a focused unit verification."""
    observed = _observed_runtime_path(signals)
    subject = observed or signals.subject
    path = f"test inputs → {subject} ┃ higher-level orchestration / transport"
    real_path = (
        "The focused production function/component executes directly in-process; "
        "the test observes its return value, raised error, or local state."
    )
    not_covered = (
        "Higher-level routing/orchestration, provider transport/network, and "
        "external-provider behavior."
    )
    if signals.temporary_filesystem:
        not_covered = (
            f"{not_covered.rstrip('.')} plus long-lived, cross-process, and "
            "host-specific filesystem behavior."
        )
    return path, real_path, not_covered


def _integration_scope(signals: _BoundarySignals) -> tuple[str, str, str]:
    """Describe the concrete integration seam exercised by one testcase."""
    observed = _observed_runtime_path(signals) or signals.module
    if signals.scripted_http:
        return (
            (f"{observed} → real HTTP client → localhost HTTP ┃ live provider"),
            (
                "Production adapter mapping, serialization/normalization, error "
                "translation, and its real HTTP client execute through the local "
                "HTTP boundary."
            ),
            (
                "Live-provider infrastructure, Internet/TLS/DNS behavior, real "
                "remote authentication, and vendor-side behavior."
            ),
        )
    if signals.vcr:
        return (
            f"{observed} → HTTP client ┃ retained VCR replay → live provider",
            (
                "Production integration code executes against the retained HTTP "
                "interaction captured from the provider boundary."
            ),
            (
                "Current live-provider availability and any provider behavior that "
                "changed after the recording was captured."
            ),
        )
    if signals.doubles:
        return (
            (f"{observed} ┃ {', '.join(signals.doubles)} → real SDK/network/provider"),
            (
                "Production adapter request/response mapping, normalization, and "
                "error translation execute against the declared client surface."
            ),
            (
                "The real SDK implementation, network transport, authentication, "
                "and remote-provider behavior."
            ),
        )
    return (
        f"{observed} → integration boundary",
        (
            "The production components invoked by this testcase execute across "
            "the integration boundary visible in the test body."
        ),
        (
            "External-system fidelity beyond what is explicitly visible in this "
            "testcase body."
        ),
    )


def _property_scope(
    value: CaseBoundaryInput,
    signals: _BoundarySignals,
) -> tuple[str, str, str]:
    """Describe generated domain, subject, and invariant boundary."""
    subject = _observed_runtime_path(signals) or signals.subject
    path = f"generated domain → {subject} → invariant"
    if value.generated_inputs:
        real_path = (
            "Hypothesis generates values from the declared strategies and repeatedly "
            "executes the production subject; the invariant is checked for each "
            "generated example."
        )
    else:
        real_path = (
            "The property-style testcase executes the production subject repeatedly, "
            "but no explicit Hypothesis strategy was recoverable from the test body."
        )
    not_covered = (
        "Values outside the declared Hypothesis strategies and higher-level "
        "system/external integrations."
    )
    if signals.temporary_filesystem:
        not_covered = (
            f"{not_covered.rstrip('.')} plus long-lived, cross-process, and "
            "host-specific filesystem behavior."
        )
    return path, real_path, not_covered


def _e2e_scope(signals: _BoundarySignals) -> tuple[str, str, str]:
    """Describe how far a system-wide workflow reaches toward production reality."""
    observed = _observed_runtime_path(signals) or "production stack"
    if signals.scripted_http:
        path = (
            f"public workflow → {observed} → HTTP client → localhost HTTP "
            "┃ live external provider"
        )
        not_covered = (
            "Live external-provider fidelity because the final remote boundary "
            "is scripted locally."
        )
    elif signals.vcr:
        path = (
            f"public workflow → {observed} → HTTP client ┃ retained VCR replay → "
            "live external provider"
        )
        not_covered = "Current live-provider behavior beyond the retained interaction."
    elif signals.doubles:
        path = f"public workflow → {observed} ┃ test double → real external system"
        not_covered = "Real external-system fidelity beyond the explicit test double."
    else:
        path = f"public workflow → {observed} → external boundary"
        not_covered = (
            "Deployment/environment differences and any external behavior not "
            "explicitly captured by this testcase."
        )
    real_path = (
        "The public workflow and production components shown by the testcase "
        "execute across the path above."
    )
    return path, real_path, not_covered


def infer_case_boundary(value: CaseBoundaryInput) -> VerificationBoundary:
    """Infer one conservative boundary from exact testcase facts."""
    signals = _boundary_signals(value)
    process, network, filesystem, external = _execution_envelope(value, signals)
    scopes = {
        "unit": lambda: _unit_scope(signals),
        "integration": lambda: _integration_scope(signals),
        "property": lambda: _property_scope(value, signals),
        "e2e": lambda: _e2e_scope(signals),
    }
    path, real_path, not_covered = scopes[value.kind]()
    extra_limits: list[str] = []
    if signals.temporary_filesystem and "filesystem behavior" not in not_covered:
        extra_limits.append(
            "long-lived, cross-process, and host-specific filesystem behavior"
        )
    if signals.patched_runtime:
        extra_limits.append("the unpatched host environment/runtime state")
    if extra_limits:
        not_covered = (
            f"{not_covered.rstrip('.')}; additionally, {'; '.join(extra_limits)}."
        )
    provenance = (
        "captured runtime evidence"
        if value.runtime is not None or value.coverage is not None
        else "source-derived fallback"
    )
    return VerificationBoundary(
        path=path,
        process=process,
        network=network,
        filesystem=filesystem,
        external=external,
        real_path=real_path,
        substitute=_substitute(signals),
        not_covered=not_covered,
        observed_proof=_observed_proof(value.checks),
        provenance=provenance,
    )
