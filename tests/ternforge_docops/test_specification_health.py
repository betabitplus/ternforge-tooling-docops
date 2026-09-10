"""Tests for the ephemeral specification-health projection."""

from __future__ import annotations

from copy import deepcopy

import pytest

from ternforge_docops._internal.sphinx.specification_health import (
    project_specification_health,
)
from ternforge_docops._internal.sphinx.specification_health_view import (
    _actionable_states,
)


def _healthy_graph() -> list[dict[str, object]]:
    """Return one fully traced Goal -> Feature -> REQ -> TREQ graph."""
    return [
        {
            "id": "GOAL_DEMO",
            "type": "goal",
            "derives_back": ["FEAT_DEMO"],
        },
        {
            "id": "FEAT_DEMO",
            "type": "feature",
            "derives": ["GOAL_DEMO"],
            "derives_back": ["REQ_DEMO"],
        },
        {
            "id": "REQ_DEMO",
            "type": "req",
            "status": "accepted",
            "revision": 2,
            "required_evidence": ["impl", "bdd"],
            "derives": ["FEAT_DEMO"],
            "derives_back": ["TREQ_DEMO"],
        },
        {
            "id": "TREQ_DEMO",
            "type": "treq",
            "status": "accepted",
            "revision": 1,
            "required_evidence": ["unit"],
            "derives": ["REQ_DEMO"],
        },
        {
            "id": "IMPL_DEMO",
            "type": "impl",
            "implements": ["REQ_DEMO[revision==2]"],
        },
        {
            "id": "TEST_BDD_DEMO",
            "type": "testcase",
            "result": "passed",
            "verification_kind": "bdd",
            "verifies": ["REQ_DEMO[revision==2]"],
        },
        {
            "id": "TEST_UNIT_DEMO",
            "type": "testcase",
            "result": "passed",
            "verification_kind": "unit",
            "verifies": ["TREQ_DEMO[revision==1]"],
        },
    ]


def test_fully_evidenced_branch_is_deeply_covered() -> None:
    """Healthy descendant evidence propagates coverage to Feature and Goal."""
    health = project_specification_health(_healthy_graph())

    assert health["TREQ_DEMO"].deep_covered is True
    assert health["REQ_DEMO"].direct_evidence_covered is True
    assert health["REQ_DEMO"].deep_covered is True
    assert health["FEAT_DEMO"].deep_covered is True
    assert health["GOAL_DEMO"].deep_covered is True


def test_missing_direct_evidence_propagates_upward() -> None:
    """A direct requirement gap blocks its Feature and Goal."""
    graph = [need for need in _healthy_graph() if need["id"] != "TEST_BDD_DEMO"]

    health = project_specification_health(graph)

    requirement = health["REQ_DEMO"]
    assert requirement.direct_evidence_covered is False
    assert requirement.missing_evidence == ("bdd",)
    assert requirement.deep_covered is False
    assert health["FEAT_DEMO"].blocked_by == ("REQ_DEMO",)
    assert health["FEAT_DEMO"].deep_covered is False
    assert health["GOAL_DEMO"].blocked_by == ("FEAT_DEMO",)
    assert health["GOAL_DEMO"].deep_covered is False


def test_constraint_gap_blocks_parent_requirement_deep_coverage_only() -> None:
    """Optional TREQ descendants participate in deep health when accepted."""
    graph = [need for need in _healthy_graph() if need["id"] != "TEST_UNIT_DEMO"]

    health = project_specification_health(graph)

    assert health["REQ_DEMO"].direct_evidence_covered is True
    assert health["REQ_DEMO"].blocked_by == ("TREQ_DEMO",)
    assert health["REQ_DEMO"].deep_covered is False
    assert health["TREQ_DEMO"].missing_evidence == ("unit",)


def test_actionable_states_report_root_cause_without_ancestor_duplicates() -> None:
    """One descendant evidence gap stays one action even when deep impact propagates."""
    graph = [need for need in _healthy_graph() if need["id"] != "TEST_UNIT_DEMO"]

    health = project_specification_health(graph)

    assert [state.need_id for state in _actionable_states(health)] == ["TREQ_DEMO"]
    assert health["REQ_DEMO"].deep_covered is False
    assert health["FEAT_DEMO"].deep_covered is False
    assert health["GOAL_DEMO"].deep_covered is False


@pytest.mark.parametrize("pin", [1, 3])
def test_noncurrent_implementation_evidence_does_not_cover_requirement(
    pin: int,
) -> None:
    """Outdated and predated implementation links cannot satisfy current evidence."""
    graph = deepcopy(_healthy_graph())
    implementation = next(need for need in graph if need["id"] == "IMPL_DEMO")
    implementation["implements"] = [f"REQ_DEMO[revision=={pin}]"]

    health = project_specification_health(graph)

    assert health["REQ_DEMO"].missing_evidence == ("impl",)
    assert health["REQ_DEMO"].direct_evidence_covered is False
    assert health["GOAL_DEMO"].deep_covered is False


@pytest.mark.parametrize("result", ["failed", "skipped", "xfail"])
def test_nonpassing_verification_cannot_satisfy_required_evidence(result: str) -> None:
    """Only passed current execution evidence closes a verification obligation."""
    graph = deepcopy(_healthy_graph())
    testcase = next(need for need in graph if need["id"] == "TEST_BDD_DEMO")
    testcase["result"] = result

    health = project_specification_health(graph)

    assert health["REQ_DEMO"].missing_evidence == ("bdd",)
    assert health["REQ_DEMO"].deep_covered is False


def test_requirement_needs_no_engineering_constraint_to_be_deeply_covered() -> None:
    """TREQ remains optional rather than becoming a mandatory decomposition level."""
    graph = [
        need
        for need in _healthy_graph()
        if need["id"] not in {"TREQ_DEMO", "TEST_UNIT_DEMO"}
    ]
    requirement = next(need for need in graph if need["id"] == "REQ_DEMO")
    requirement["derives_back"] = []

    health = project_specification_health(graph)

    assert health["REQ_DEMO"].deep_covered is True
    assert health["FEAT_DEMO"].deep_covered is True
    assert health["GOAL_DEMO"].deep_covered is True


def test_deprecated_constraint_does_not_block_active_contract() -> None:
    """Deprecated descendants are outside active deep-coverage obligations."""
    graph = deepcopy(_healthy_graph())
    constraint = next(need for need in graph if need["id"] == "TREQ_DEMO")
    constraint["status"] = "deprecated"
    graph = [need for need in graph if need["id"] != "TEST_UNIT_DEMO"]

    health = project_specification_health(graph)

    assert "TREQ_DEMO" not in health
    assert health["REQ_DEMO"].deep_covered is True


def test_feature_with_only_draft_requirements_is_not_deeply_covered() -> None:
    """Structural decomposition alone is not active specification coverage."""
    graph = deepcopy(_healthy_graph())
    requirement = next(need for need in graph if need["id"] == "REQ_DEMO")
    requirement["status"] = "draft"

    health = project_specification_health(graph)

    assert health["FEAT_DEMO"].structural_covered is True
    assert health["FEAT_DEMO"].deep_covered is False
    assert health["FEAT_DEMO"].gap_reason == "No accepted requirement"
    assert health["GOAL_DEMO"].deep_covered is False
