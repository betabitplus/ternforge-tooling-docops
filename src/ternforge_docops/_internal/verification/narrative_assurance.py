"""Assurance-specific RST cards for non-BDD verification narratives."""

from __future__ import annotations

from typing import Protocol

from ternforge_docops._internal.verification.assurance import (
    VerificationBoundary,
    boundary_interaction_text,
)
from ternforge_docops._internal.verification.evidence import VerificationRuntimeEvidence

_TICK = chr(96)


class AssuranceNarrativeCase(Protocol):
    """Minimal testcase view required by assurance-specific rendering."""

    kind: str
    generated_inputs: tuple[str, ...]
    runtime: VerificationRuntimeEvidence | None
    boundary: VerificationBoundary | None


def _literal(value: str) -> str:
    """Render one compact RST inline literal."""
    return f"{_TICK}{_TICK}{value.replace(_TICK, '')}{_TICK}{_TICK}"


def _has_runtime_marker(case: AssuranceNarrativeCase, marker: str) -> bool:
    """Return whether retained runtime evidence captured one execution marker."""
    return case.runtime is not None and marker.casefold() in {
        value.casefold() for value in case.runtime.markers
    }


def method_sentence(case: AssuranceNarrativeCase) -> str:
    """Describe the verification method without status or execution trivia."""
    if case.kind == "unit":
        return (
            "Exercises focused logic directly and checks the observable values or "
            "errors that define this contract."
        )
    if case.kind == "integration":
        return (
            "Exercises the component through a controlled integration boundary and "
            "checks the data or errors observed across that boundary."
        )
    if case.kind == "property":
        if _has_runtime_marker(case, "hypothesis"):
            return (
                "Captured runtime evidence confirms Hypothesis execution; the testcase "
                "checks the invariant across generated examples."
            )
        return (
            "This testcase is classified as property verification, but retained "
            "runtime evidence does not establish Hypothesis-generated execution."
        )
    return (
        "Exercises the public workflow end to end and checks the resulting observable "
        "behavior."
    )


def _render_boundary_interactions(
    lines: list[str],
    boundary: VerificationBoundary,
    indent: int,
) -> None:
    """Render every explicitly captured boundary interaction independently."""
    if not boundary.interactions:
        return
    prefix = " " * indent
    lines.append(f"{prefix}**Captured boundary interactions:**")
    lines.append("")
    lines.extend(
        f"{prefix}* {_literal(boundary_interaction_text(interaction))}"
        for interaction in boundary.interactions
    )
    lines.append("")


def _render_property_model(
    lines: list[str],
    case: AssuranceNarrativeCase,
) -> None:
    """Separate captured property execution from source-derived fallback details."""
    hypothesis = _has_runtime_marker(case, "hypothesis")
    proof_model = (
        "Hypothesis generated examples → production subject → invariant"
        if hypothesis
        else "property classification → production subject → invariant"
    )
    execution = (
        "Hypothesis · captured runtime evidence"
        if hypothesis
        else "Hypothesis execution not captured"
    )
    generator_basis = (
        "source-derived generator declaration"
        if case.generated_inputs
        else "generator declaration unavailable"
    )
    lines.extend(
        (
            ".. card:: Property proof",
            "",
            f"   **Proof model:** {proof_model}",
            "",
            f"   **Execution mechanism:** {execution}",
            "",
            f"   **Generator declaration basis:** {generator_basis}",
            "",
        )
    )
    explanation = (
        (
            "   Captured runtime evidence establishes generated-example execution. "
            "The strategy text below is source enrichment and does not replace "
            "runtime evidence."
        )
        if hypothesis
        else (
            "   The property classification and any source-declared strategies do not "
            "by themselves prove that Hypothesis generated examples in this retained "
            "execution."
        )
    )
    lines.extend((explanation, ""))


def _render_e2e_reach(
    lines: list[str],
    boundary: VerificationBoundary | None,
) -> None:
    """Explain end-to-end reach without treating E2E as automatic live fidelity."""
    lines.extend(
        (
            ".. card:: End-to-end reach",
            "",
            "   **Entry:** public workflow",
            "",
        )
    )
    if boundary is not None and boundary.interactions:
        lines.append("   **Terminal interactions:**")
        lines.append("")
        lines.extend(
            f"   * {_literal(boundary_interaction_text(interaction))}"
            for interaction in boundary.interactions
        )
        lines.append("")
    else:
        lines.extend(
            (
                "   **Terminal interactions:** no captured boundary interaction.",
                "",
            )
        )
    lines.extend(
        (
            (
                "   End-to-end means the public workflow reaches the observed "
                "production path. Live external-system fidelity is claimed only when "
                "a direct live interaction is explicitly captured."
            ),
            "",
        )
    )


def render_boundary(lines: list[str], boundary: VerificationBoundary) -> None:
    """Render the verification scope before exercise/assertion details."""
    lines.extend(
        (
            ".. card:: Verification boundary",
            "",
            f"   **Path:** {_literal(boundary.path)}",
            "",
            (
                "   **Execution envelope:** "
                f":bdg-secondary:{_TICK}Process · {boundary.process}{_TICK} "
                f":bdg-secondary:{_TICK}Network · {boundary.network}{_TICK} "
                f":bdg-secondary:{_TICK}Filesystem · {boundary.filesystem}{_TICK} "
                f":bdg-secondary:{_TICK}External · {boundary.external}{_TICK}"
            ),
            "",
            f"   * **Real path:** {boundary.real_path}",
            f"   * **Substitute:** {boundary.substitute}",
            f"   * **Not covered:** {boundary.not_covered}",
            "",
        )
    )
    _render_boundary_interactions(lines, boundary, 3)
    lines.extend(
        (
            "   .. dropdown:: How this verification establishes the proof",
            "",
            f"      **Observed proof:** {_literal(boundary.observed_proof)}",
            "",
            f"      **Boundary basis:** {boundary.provenance}",
            "",
        )
    )


def render_case_specialization(
    lines: list[str],
    case: AssuranceNarrativeCase,
) -> None:
    """Render verification-kind-specific assurance detail."""
    if case.kind == "property":
        _render_property_model(lines, case)
    elif case.kind == "e2e":
        _render_e2e_reach(lines, case.boundary)
