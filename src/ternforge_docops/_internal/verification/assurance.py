"""Shared assurance semantics for human verification views."""

from __future__ import annotations

from dataclasses import dataclass

from ternforge_docops._internal.verification.coverage_evidence import (
    CoverageFootprint,
    production_modules,
)
from ternforge_docops._internal.verification.evidence import (
    BoundaryInteractionObservation,
    ExternalSubstituteObservation,
    VerificationRuntimeEvidence,
    boundary_interactions,
    external_substitutes,
)


@dataclass(frozen=True)
class VerificationBoundary:
    """Observed execution scope, interactions, substitutions, proof, and limits."""

    path: str
    real_path: str
    substitute: str
    not_covered: str
    observed_proof: str
    injected_condition: str = ""
    process: str = "not captured"
    network: str = "not captured"
    filesystem: str = "not captured"
    external: str = "not captured"
    provenance: str = "source-derived fallback"
    interactions: tuple[BoundaryInteractionObservation, ...] = ()


def boundary_interaction_text(value: BoundaryInteractionObservation) -> str:
    """Render one captured interaction without adding assurance interpretation."""
    parts = (
        value.boundary,
        value.interaction,
        f"{value.participant} → {value.target}",
        value.transport,
    )
    return " · ".join(part for part in parts if part)


@dataclass(frozen=True)
class RuntimeAssuranceFacts:
    """Objective execution facts shared by BDD and non-BDD assurance views."""

    mechanism: str
    modules: tuple[str, ...]
    interactions: tuple[BoundaryInteractionObservation, ...]
    substitutes: tuple[ExternalSubstituteObservation, ...]
    fixtures: tuple[str, ...]
    markers: tuple[str, ...]
    process: str
    filesystem: str
    network: str
    external: str
    provenance: str


def _has_scripted_http(
    substitutes: tuple[ExternalSubstituteObservation, ...],
) -> bool:
    """Return whether captured substitutions include the shared HTTP test server."""
    return any(
        item.producer == "ScriptedHTTPServer" or item.mode == "local-scripted-http"
        for item in substitutes
    )


def _runtime_mechanism(
    runtime: VerificationRuntimeEvidence,
    interactions: tuple[BoundaryInteractionObservation, ...],
    substitutes: tuple[ExternalSubstituteObservation, ...],
) -> str:
    """Classify only mechanisms captured by the executing test."""
    markers = {value.casefold() for value in runtime.markers}
    fixtures = {value.casefold() for value in runtime.fixtures}
    relations = {value.interaction.casefold() for value in interactions}
    candidates = (
        ("scripted-http", _has_scripted_http(substitutes)),
        ("external-double", bool(substitutes)),
        ("boundary-replay", "replay" in relations),
        ("boundary-direct", "direct" in relations),
        ("vcr", "vcr" in markers),
        ("temporary-filesystem", bool({"tmp_path", "tmp_path_factory"} & fixtures)),
        ("patched-runtime", "monkeypatch" in fixtures),
        ("hermetic", "hermetic" in markers),
    )
    return next((name for name, active in candidates if active), "direct")


def _interaction_targets(
    interactions: tuple[BoundaryInteractionObservation, ...],
    relation: str,
) -> tuple[str, ...]:
    """Return unique targets for one captured interaction relation."""
    return tuple(
        dict.fromkeys(
            item.target
            for item in interactions
            if item.interaction.casefold() == relation and item.target
        )
    )


def _interaction_transports(
    interactions: tuple[BoundaryInteractionObservation, ...],
    relation: str,
) -> tuple[str, ...]:
    """Return unique transports for one captured interaction relation."""
    return tuple(
        dict.fromkeys(
            item.transport
            for item in interactions
            if item.interaction.casefold() == relation and item.transport
        )
    )


def _interaction_participants(
    interactions: tuple[BoundaryInteractionObservation, ...],
    relation: str,
) -> tuple[str, ...]:
    """Return unique participants for one captured interaction relation."""
    return tuple(
        dict.fromkeys(
            item.participant
            for item in interactions
            if item.interaction.casefold() == relation and item.participant
        )
    )


def _external_label(
    mechanism: str,
    interactions: tuple[BoundaryInteractionObservation, ...],
    substitutes: tuple[ExternalSubstituteObservation, ...],
) -> str:
    """Describe all externally participating systems from captured facts."""
    if mechanism == "scripted-http":
        return "scripted provider"
    labels: list[str] = []
    substitute_participants = _interaction_participants(interactions, "substitute")
    if substitute_participants:
        labels.append(f"{', '.join(substitute_participants)} test double")
    replay_targets = _interaction_targets(interactions, "replay")
    if replay_targets:
        labels.append(f"replayed {', '.join(replay_targets)}")
    direct_targets = _interaction_targets(interactions, "direct")
    if direct_targets:
        labels.append(f"direct {', '.join(direct_targets)}")
    if labels:
        return "; ".join(labels)
    static = {
        "vcr": "recorded provider interaction",
        "patched-runtime": "patched runtime dependency",
        "hermetic": "hermetic local resources",
    }
    if mechanism in static:
        return static[mechanism]
    if mechanism == "external-double":
        return ", ".join(item.producer for item in substitutes) + " test double"
    return ""


def _has_interaction(
    interactions: tuple[BoundaryInteractionObservation, ...],
    relation: str,
) -> bool:
    """Return whether one interaction relation was captured."""
    return any(item.interaction.casefold() == relation for item in interactions)


def _interaction_transport_label(
    interactions: tuple[BoundaryInteractionObservation, ...],
    relation: str,
    prefix: str,
) -> str:
    """Render one transport label from captured interaction facts."""
    transports = _interaction_transports(interactions, relation)
    if transports:
        return f"{prefix} {', '.join(transports)}"
    return f"{prefix} boundary" if _has_interaction(interactions, relation) else ""


def _interaction_network_label(
    interactions: tuple[BoundaryInteractionObservation, ...],
) -> str:
    """Render all captured interaction transports without collapsing them."""
    labels = (
        _interaction_transport_label(interactions, "substitute", "substituted"),
        _interaction_transport_label(interactions, "replay", "replayed"),
        _interaction_transport_label(interactions, "direct", "direct"),
    )
    return "; ".join(value for value in labels if value)


def _legacy_network_label(
    mechanism: str,
    substitutes: tuple[ExternalSubstituteObservation, ...],
) -> str:
    """Render network summary for retained legacy evidence."""
    if mechanism == "vcr":
        return "recorded HTTP replay"
    if mechanism != "external-double":
        return ""
    transports = tuple(
        dict.fromkeys(item.transport for item in substitutes if item.transport)
    )
    return (
        f"substituted {', '.join(transports)}" if transports else "substituted boundary"
    )


def _network_label(
    mechanism: str,
    interactions: tuple[BoundaryInteractionObservation, ...],
    substitutes: tuple[ExternalSubstituteObservation, ...],
) -> str:
    """Describe every captured network/transport interaction without collapsing it."""
    if mechanism == "scripted-http":
        return "localhost HTTP"
    captured = _interaction_network_label(interactions)
    return captured or _legacy_network_label(mechanism, substitutes)


def runtime_assurance_facts(
    runtime: VerificationRuntimeEvidence | None,
    coverage: CoverageFootprint | None,
) -> RuntimeAssuranceFacts | None:
    """Return one normalized fact set without inferring uncaptured assurance claims."""
    if runtime is None and coverage is None:
        return None
    interactions = boundary_interactions(runtime)
    substitutes = external_substitutes(runtime)
    modules = production_modules(coverage)
    if runtime is None:
        return RuntimeAssuranceFacts(
            mechanism="unknown",
            modules=modules,
            interactions=(),
            substitutes=(),
            fixtures=(),
            markers=(),
            process="not captured",
            filesystem="not captured",
            network="not captured",
            external="not captured",
            provenance="captured coverage evidence",
        )
    fixtures = tuple(runtime.fixtures)
    markers = tuple(runtime.markers)
    mechanism = _runtime_mechanism(runtime, interactions, substitutes)
    fixture_set = {value.casefold() for value in fixtures}
    return RuntimeAssuranceFacts(
        mechanism=mechanism,
        modules=modules,
        interactions=interactions,
        substitutes=substitutes,
        fixtures=fixtures,
        markers=markers,
        process="subprocess" if "subprocess" in fixture_set else "in-process",
        filesystem=(
            "temporary"
            if {"tmp_path", "tmp_path_factory"} & fixture_set
            else "not exercised"
        ),
        network=_network_label(mechanism, interactions, substitutes),
        external=_external_label(mechanism, interactions, substitutes),
        provenance="captured runtime evidence",
    )
