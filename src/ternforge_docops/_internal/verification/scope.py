"""Evidence-derived verification scope used by assurance projections."""

from __future__ import annotations

from dataclasses import dataclass

from ternforge_docops._internal.verification.assurance import runtime_assurance_facts
from ternforge_docops._internal.verification.coverage_evidence import CoverageFootprint
from ternforge_docops._internal.verification.evidence import VerificationRuntimeEvidence

SCOPE_ORDER = (
    "focused_logic",
    "component",
    "integration_boundary",
    "transport_sdk_filesystem",
    "public_workflow",
    "live_external_reality",
)
SCOPE_LABELS = {
    "focused_logic": "Focused logic",
    "component": "Component",
    "integration_boundary": "Integration boundary",
    "transport_sdk_filesystem": "Transport / SDK / filesystem",
    "public_workflow": "Public workflow / system",
    "live_external_reality": "Live external reality",
}
_SCOPE_INDEX = {value: index for index, value in enumerate(SCOPE_ORDER)}


@dataclass(frozen=True, slots=True)
class VerificationScope:
    """Conservative observed reach for one concrete verification execution."""

    reach: str
    basis: str
    external_reach: str

    @property
    def rank(self) -> int:
        """Return the ordered ladder rank for comparison and rendering."""
        return _SCOPE_INDEX.get(self.reach, -1)


def scope_rank(value: object) -> int:
    """Return the ordered scope rank for one serialized scope value."""
    return _SCOPE_INDEX.get(str(value or ""), -1)


def scope_path(reach: object) -> tuple[str, ...]:
    """Return the ladder prefix reached by one evidence item."""
    rank = scope_rank(reach)
    return SCOPE_ORDER[: rank + 1] if rank >= 0 else ()


def _coverage_scope(
    coverage: CoverageFootprint | None,
    modules: tuple[str, ...],
) -> tuple[str, list[str]]:
    """Derive the local/component rung from retained production coverage."""
    if coverage is None or not modules:
        return "focused_logic", []
    reach = "component" if len(modules) > 1 else "focused_logic"
    return reach, ["captured production coverage"]


def _boundary_scope(
    reach: str,
    basis: list[str],
    *,
    has_boundary: bool,
    has_transport: bool,
) -> tuple[str, list[str]]:
    """Raise local scope only when boundary or transport facts are captured."""
    if has_boundary:
        reach = "integration_boundary"
        basis.append("captured boundary interaction")
    if has_transport:
        reach = "transport_sdk_filesystem"
        basis.append("captured transport/filesystem reach")
    return reach, basis


def _external_scope(
    relations: set[str],
    *,
    has_substitutes: bool,
) -> tuple[str, str | None]:
    """Return observed external relation plus a live-scope promotion."""
    if "direct" in relations:
        return "direct", "live_external_reality"
    if "replay" in relations:
        return "replay", None
    if "substitute" in relations or has_substitutes:
        return "substitute", None
    return "local", None


def _runtime_scope(
    runtime: VerificationRuntimeEvidence | None,
    coverage: CoverageFootprint | None,
) -> tuple[str, list[str], str]:
    """Project captured runtime facts onto the scope ladder."""
    facts = runtime_assurance_facts(runtime, coverage)
    modules = () if facts is None else facts.modules
    reach, basis = _coverage_scope(coverage, modules)
    if facts is None:
        return reach, basis, "local"

    relations = {item.interaction.casefold() for item in facts.interactions}
    reach, basis = _boundary_scope(
        reach,
        basis,
        has_boundary=bool(facts.interactions or facts.substitutes),
        has_transport=(
            facts.network not in {"", "not captured", "not exercised"}
            or facts.filesystem == "temporary"
        ),
    )
    external_reach, promoted = _external_scope(
        relations,
        has_substitutes=bool(facts.substitutes),
    )
    if promoted is not None:
        reach = promoted
        basis.append("captured direct external interaction")
    return reach, basis, external_reach


def verification_scope(
    runtime: VerificationRuntimeEvidence | None,
    coverage: CoverageFootprint | None,
    *,
    gherkin_feature: str = "",
) -> VerificationScope:
    """Derive scope from captured facts without using verification-kind shortcuts."""
    reach, basis, external_reach = _runtime_scope(runtime, coverage)
    if gherkin_feature.strip() and scope_rank(reach) < scope_rank("public_workflow"):
        reach = "public_workflow"
        basis.append("executed Gherkin workflow")
    if not basis:
        basis.append("traced test execution")
    return VerificationScope(
        reach=reach,
        basis="; ".join(dict.fromkeys(basis)),
        external_reach=external_reach,
    )
