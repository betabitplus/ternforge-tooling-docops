"""Shared assurance semantics for human verification views."""

from __future__ import annotations

from dataclasses import dataclass

from ternforge_docops._internal.verification.coverage_evidence import (
    CoverageFootprint,
    production_modules,
)
from ternforge_docops._internal.verification.evidence import (
    ExternalSubstituteObservation,
    VerificationRuntimeEvidence,
    external_substitutes,
)


@dataclass(frozen=True)
class VerificationBoundary:
    """Observed execution scope, substitutions, proof, and explicit limits."""

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


@dataclass(frozen=True)
class RuntimeAssuranceFacts:
    """Objective execution facts shared by BDD and non-BDD assurance views."""

    mechanism: str
    modules: tuple[str, ...]
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
        item.boundary == "provider-http" or item.producer == "ScriptedHTTPServer"
        for item in substitutes
    )


def _runtime_mechanism(
    runtime: VerificationRuntimeEvidence,
    substitutes: tuple[ExternalSubstituteObservation, ...],
) -> str:
    """Classify only mechanisms captured by the executing test."""
    markers = {value.casefold() for value in runtime.markers}
    fixtures = {value.casefold() for value in runtime.fixtures}
    candidates = (
        ("scripted-http", _has_scripted_http(substitutes)),
        ("external-double", bool(substitutes)),
        ("vcr", "vcr" in markers),
        ("temporary-filesystem", bool({"tmp_path", "tmp_path_factory"} & fixtures)),
        ("patched-runtime", "monkeypatch" in fixtures),
        ("hermetic", "hermetic" in markers),
    )
    return next((name for name, active in candidates if active), "direct")


def _external_label(
    mechanism: str,
    substitutes: tuple[ExternalSubstituteObservation, ...],
) -> str:
    """Describe externally participating systems from captured facts only."""
    if mechanism == "scripted-http":
        return "scripted provider"
    if mechanism == "vcr":
        return "recorded provider interaction"
    if mechanism == "external-double":
        return ", ".join(item.producer for item in substitutes) + " test double"
    if mechanism == "patched-runtime":
        return "patched runtime dependency"
    if mechanism == "hermetic":
        return "hermetic local resources"
    return ""


def _network_label(
    mechanism: str,
    substitutes: tuple[ExternalSubstituteObservation, ...],
) -> str:
    """Describe the captured network/transport mechanism when explicit."""
    if mechanism == "scripted-http":
        return "localhost HTTP"
    if mechanism == "vcr":
        return "recorded HTTP replay"
    if mechanism == "external-double":
        transports = tuple(
            dict.fromkeys(item.transport for item in substitutes if item.transport)
        )
        return (
            f"substituted {', '.join(transports)}"
            if transports
            else "substituted boundary"
        )
    return ""


def runtime_assurance_facts(
    runtime: VerificationRuntimeEvidence | None,
    coverage: CoverageFootprint | None,
) -> RuntimeAssuranceFacts | None:
    """Return one normalized fact set without inferring uncaptured assurance claims."""
    if runtime is None and coverage is None:
        return None
    substitutes = external_substitutes(runtime)
    modules = production_modules(coverage)
    if runtime is None:
        return RuntimeAssuranceFacts(
            mechanism="unknown",
            modules=modules,
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
    mechanism = _runtime_mechanism(runtime, substitutes)
    fixture_set = {value.casefold() for value in fixtures}
    return RuntimeAssuranceFacts(
        mechanism=mechanism,
        modules=modules,
        substitutes=substitutes,
        fixtures=fixtures,
        markers=markers,
        process="subprocess" if "subprocess" in fixture_set else "in-process",
        filesystem=(
            "temporary"
            if {"tmp_path", "tmp_path_factory"} & fixture_set
            else "not exercised"
        ),
        network=_network_label(mechanism, substitutes),
        external=_external_label(mechanism, substitutes),
        provenance="captured runtime evidence",
    )
