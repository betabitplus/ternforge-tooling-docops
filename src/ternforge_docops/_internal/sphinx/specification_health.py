"""Ephemeral specification-health projection over the authoritative Needs graph."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from ternforge_docops._internal.sphinx.traceability import revision_pinned_targets

_VERIFICATION_KINDS = frozenset({"bdd", "unit", "property", "integration", "e2e"})
_ACTIVE_STATUS = "accepted"


@dataclass(frozen=True, slots=True)
class SpecificationHealth:
    """Derived coverage state for one authored specification node."""

    need_id: str
    need_type: str
    structural_covered: bool
    direct_evidence_covered: bool | None
    deep_covered: bool
    missing_evidence: tuple[str, ...] = ()
    blocked_by: tuple[str, ...] = ()
    gap_reason: str | None = None


def _ids(value: object) -> tuple[str, ...]:
    """Normalize one resolved Needs link field to stable identifiers."""
    if isinstance(value, str):
        values = value.split(",")
    elif isinstance(value, list | tuple):
        values = value
    else:
        return ()
    return tuple(
        str(item).strip().split("[", 1)[0] for item in values if str(item).strip()
    )


def _string_set(value: object) -> frozenset[str]:
    """Normalize a small string-list Need field without assuming its runtime shape."""
    if isinstance(value, str):
        values = value.split(",")
    elif isinstance(value, list | tuple | set | frozenset):
        values = value
    else:
        return frozenset()
    return frozenset(str(item).strip() for item in values if str(item).strip())


def _current_target(
    by_id: Mapping[str, Mapping[str, object]],
    target_id: str,
    pinned_revision: int,
) -> bool:
    """Return whether a revision pin targets the current authored contract revision."""
    target = by_id.get(target_id)
    return target is not None and target.get("revision") == pinned_revision


def _evidence_source(need: Mapping[str, object]) -> tuple[str, str] | None:
    """Return the evidence kind and link field contributed by one graph node."""
    need_type = str(need.get("type") or "")
    if need_type == "impl":
        return "impl", "implements"
    if need_type != "testcase" or str(need.get("result") or "") != "passed":
        return None
    kind = str(need.get("verification_kind") or "")
    return (kind, "verifies") if kind in _VERIFICATION_KINDS else None


def _satisfied_evidence(
    needs: Iterable[Mapping[str, object]],
    by_id: Mapping[str, Mapping[str, object]],
) -> dict[str, frozenset[str]]:
    """Collect only current implementation and passed verification evidence."""
    satisfied: dict[str, set[str]] = defaultdict(set)
    for need in needs:
        source = _evidence_source(need)
        if source is None:
            continue
        kind, link_type = source
        for target_id, revision in revision_pinned_targets(need, link_type):
            if _current_target(by_id, target_id, revision):
                satisfied[target_id].add(kind)
    return {need_id: frozenset(kinds) for need_id, kinds in satisfied.items()}


def _active_nodes(
    by_id: Mapping[str, Mapping[str, object]],
    need_type: str,
) -> dict[str, Mapping[str, object]]:
    """Select accepted requirement-like nodes of one type."""
    return {
        need_id: need
        for need_id, need in by_id.items()
        if need.get("type") == need_type and need.get("status") == _ACTIVE_STATUS
    }


def _contract_health(
    need: Mapping[str, object],
    evidence: Mapping[str, frozenset[str]],
    *,
    missing_parent: str,
    blocked_by: tuple[str, ...] = (),
) -> SpecificationHealth:
    """Project one accepted REQ/TREQ from parent linkage and required evidence."""
    need_id = str(need["id"])
    required = _string_set(need.get("required_evidence"))
    missing = tuple(sorted(required - evidence.get(need_id, frozenset())))
    structural = bool(_ids(need.get("derives")))
    direct = not missing
    return SpecificationHealth(
        need_id=need_id,
        need_type=str(need["type"]),
        structural_covered=structural,
        direct_evidence_covered=direct,
        deep_covered=structural and direct and not blocked_by,
        missing_evidence=missing,
        blocked_by=blocked_by,
        gap_reason=None if structural else missing_parent,
    )


def _project_constraints(
    constraints: Mapping[str, Mapping[str, object]],
    evidence: Mapping[str, frozenset[str]],
) -> dict[str, SpecificationHealth]:
    """Project accepted engineering constraints."""
    return {
        need_id: _contract_health(
            need,
            evidence,
            missing_parent="Missing requirement parent",
        )
        for need_id, need in constraints.items()
    }


def _project_requirements(
    requirements: Mapping[str, Mapping[str, object]],
    constraints: Mapping[str, Mapping[str, object]],
    evidence: Mapping[str, frozenset[str]],
    result: Mapping[str, SpecificationHealth],
) -> dict[str, SpecificationHealth]:
    """Project accepted requirements including active constraint descendants."""
    projected: dict[str, SpecificationHealth] = {}
    for need_id, need in requirements.items():
        child_ids = tuple(
            child_id
            for child_id in _ids(need.get("derives_back"))
            if child_id in constraints
        )
        blocked = tuple(
            child_id for child_id in child_ids if not result[child_id].deep_covered
        )
        projected[need_id] = _contract_health(
            need,
            evidence,
            missing_parent="Missing feature parent",
            blocked_by=blocked,
        )
    return projected


def _feature_health(
    need_id: str,
    need: Mapping[str, object],
    by_id: Mapping[str, Mapping[str, object]],
    requirements: Mapping[str, Mapping[str, object]],
    result: Mapping[str, SpecificationHealth],
) -> SpecificationHealth:
    """Project one Feature from authored and active Requirement descendants."""
    all_children = tuple(
        child_id
        for child_id in _ids(need.get("derives_back"))
        if by_id.get(child_id, {}).get("type") == "req"
    )
    active_children = tuple(
        child_id for child_id in all_children if child_id in requirements
    )
    blocked = tuple(
        child_id for child_id in active_children if not result[child_id].deep_covered
    )
    if not all_children:
        reason = "Missing product requirement decomposition"
    elif not active_children:
        reason = "No accepted requirement"
    else:
        reason = None
    return SpecificationHealth(
        need_id=need_id,
        need_type="feature",
        structural_covered=bool(all_children),
        direct_evidence_covered=None,
        deep_covered=bool(active_children) and not blocked,
        blocked_by=blocked,
        gap_reason=reason,
    )


def _project_features(
    features: Mapping[str, Mapping[str, object]],
    by_id: Mapping[str, Mapping[str, object]],
    requirements: Mapping[str, Mapping[str, object]],
    result: Mapping[str, SpecificationHealth],
) -> dict[str, SpecificationHealth]:
    """Project all Features after Requirement health is known."""
    return {
        need_id: _feature_health(need_id, need, by_id, requirements, result)
        for need_id, need in features.items()
    }


def _goal_health(
    need_id: str,
    need: Mapping[str, object],
    features: Mapping[str, Mapping[str, object]],
    result: Mapping[str, SpecificationHealth],
) -> SpecificationHealth:
    """Project one Goal from Feature descendants."""
    child_ids = tuple(
        child_id for child_id in _ids(need.get("derives_back")) if child_id in features
    )
    blocked = tuple(
        child_id for child_id in child_ids if not result[child_id].deep_covered
    )
    structural = bool(child_ids)
    return SpecificationHealth(
        need_id=need_id,
        need_type="goal",
        structural_covered=structural,
        direct_evidence_covered=None,
        deep_covered=structural and not blocked,
        blocked_by=blocked,
        gap_reason=None if structural else "Missing feature decomposition",
    )


def _project_goals(
    goals: Mapping[str, Mapping[str, object]],
    features: Mapping[str, Mapping[str, object]],
    result: Mapping[str, SpecificationHealth],
) -> dict[str, SpecificationHealth]:
    """Project all Goals after Feature health is known."""
    return {
        need_id: _goal_health(need_id, need, features, result)
        for need_id, need in goals.items()
    }


def project_specification_health(
    needs: Iterable[Mapping[str, object]],
) -> dict[str, SpecificationHealth]:
    """Project recursive health from the authoritative graph without storing a copy."""
    items = list(needs)
    by_id = {str(need["id"]): need for need in items if need.get("id")}
    evidence = _satisfied_evidence(items, by_id)
    constraints = _active_nodes(by_id, "treq")
    requirements = _active_nodes(by_id, "req")
    features = {
        need_id: need
        for need_id, need in by_id.items()
        if need.get("type") == "feature"
    }
    goals = {
        need_id: need for need_id, need in by_id.items() if need.get("type") == "goal"
    }

    result = _project_constraints(constraints, evidence)
    result.update(_project_requirements(requirements, constraints, evidence, result))
    result.update(_project_features(features, by_id, requirements, result))
    result.update(_project_goals(goals, features, result))
    return result
