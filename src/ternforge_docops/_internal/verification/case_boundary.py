"""Boundary semantics for source-enriched non-BDD verification narratives."""

from __future__ import annotations

from ternforge_docops._internal.verification.assurance import (
    RuntimeAssuranceFacts,
    VerificationBoundary,
)
from ternforge_docops._internal.verification.case_signals import (
    BoundarySignals as _BoundarySignals,
    CaseBoundaryInput,
    boundary_signals as _boundary_signals,
)
from ternforge_docops._internal.verification.interactions import (
    BoundaryInteractionObservation,
)
from ternforge_docops._internal.verification.source_analysis import (
    observed_proof as _observed_proof,
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
    if facts is not None and facts.substitutes:
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
    if signals.replay:
        return (
            f"{observed} ┃ captured boundary replay → external system",
            (
                "Production integration code executes against the explicitly captured "
                "replay interaction."
            ),
            "Current external-system behavior beyond the captured replay.",
        )
    if signals.direct_external:
        return (
            f"{observed} → integration boundary → live external system",
            (
                "Production integration code executes through an explicitly captured "
                "direct external interaction."
            ),
            (
                "External behavior outside this captured run and deployment-specific "
                "environment differences."
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
    """Describe captured property execution without promoting source declarations."""
    subject = _observed_runtime_path(signals) or signals.subject
    if signals.hypothesis:
        path = f"Hypothesis generated domain → {subject} → invariant"
        if value.generated_inputs:
            real_path = (
                "Captured pytest runtime confirms Hypothesis execution. The declared "
                "strategies shown below come from source enrichment and describe the "
                "generator domain; the invariant is checked by the executed testcase."
            )
            not_covered = (
                "Values outside the source-declared Hypothesis strategies and "
                "higher-level system/external integrations."
            )
        else:
            real_path = (
                "Captured pytest runtime confirms Hypothesis execution, but retained "
                "evidence does not expose the generator declaration."
            )
            not_covered = (
                "The exact generated domain is not available from retained evidence, "
                "plus higher-level system/external integrations."
            )
    else:
        path = f"property-classified testcase → {subject} → invariant"
        real_path = (
            "The testcase is classified as property verification, but retained runtime "
            "evidence does not contain the public Hypothesis pytest marker."
        )
        not_covered = (
            "Generated-domain execution is not established by retained runtime "
            "evidence, plus higher-level system/external integrations."
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
    elif signals.replay:
        path = f"public workflow → {observed} ┃ captured replay → external system"
        not_covered = "Current external-system behavior beyond the captured replay."
    elif signals.direct_external:
        path = f"public workflow → {observed} → live external boundary"
        not_covered = (
            "Deployment/environment variability and external behavior outside this "
            "captured live interaction."
        )
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


def _scope(
    value: CaseBoundaryInput,
    signals: _BoundarySignals,
) -> tuple[str, str, str]:
    """Select the semantic scope renderer for one verification kind."""
    scopes = {
        "unit": lambda: _unit_scope(signals),
        "integration": lambda: _integration_scope(signals),
        "property": lambda: _property_scope(value, signals),
        "e2e": lambda: _e2e_scope(signals),
    }
    return scopes[value.kind]()


def _with_environment_limits(
    not_covered: str,
    signals: _BoundarySignals,
) -> str:
    """Append independent environment limits without duplicating existing wording."""
    extra_limits: list[str] = []
    if signals.temporary_filesystem and "filesystem behavior" not in not_covered:
        extra_limits.append(
            "long-lived, cross-process, and host-specific filesystem behavior"
        )
    if signals.patched_runtime:
        extra_limits.append("the unpatched host environment/runtime state")
    if not extra_limits:
        return not_covered
    return f"{not_covered.rstrip('.')}; additionally, {'; '.join(extra_limits)}."


def _boundary_provenance(
    value: CaseBoundaryInput,
    signals: _BoundarySignals,
) -> str:
    """Describe which retained sources establish this boundary."""
    property_runtime = value.kind == "property" and value.runtime is not None
    if property_runtime and signals.hypothesis and value.generated_inputs:
        return "captured runtime evidence + source-derived generator declaration"
    if property_runtime and not signals.hypothesis:
        return "captured runtime evidence; Hypothesis execution not captured"
    if value.runtime is not None or value.coverage is not None:
        return "captured runtime evidence"
    return "source-derived fallback"


def _captured_interactions(
    signals: _BoundarySignals,
) -> tuple[BoundaryInteractionObservation, ...]:
    """Return captured interactions without exposing assurance internals."""
    return signals.assurance.interactions if signals.assurance is not None else ()


def infer_case_boundary(value: CaseBoundaryInput) -> VerificationBoundary:
    """Infer one conservative boundary from exact testcase facts."""
    signals = _boundary_signals(value)
    process, network, filesystem, external = _execution_envelope(value, signals)
    path, real_path, not_covered = _scope(value, signals)
    return VerificationBoundary(
        path=path,
        process=process,
        network=network,
        filesystem=filesystem,
        external=external,
        real_path=real_path,
        substitute=_substitute(signals),
        not_covered=_with_environment_limits(not_covered, signals),
        observed_proof=_observed_proof(value.checks),
        provenance=_boundary_provenance(value, signals),
        interactions=_captured_interactions(signals),
    )
