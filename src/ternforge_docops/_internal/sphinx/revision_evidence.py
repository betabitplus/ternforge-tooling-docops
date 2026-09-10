"""Revision-current verification evidence accounting over Sphinx-Needs links."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping

from ternforge_docops._internal.sphinx.traceability import revision_pinned_targets

VERIFICATION_KINDS = ("bdd", "unit", "integration", "property", "e2e")
type EvidenceCounts = tuple[int, int, int, int]


def _verification_source(need: Mapping[str, object]) -> tuple[str, bool] | None:
    """Return one supported testcase kind and whether that execution passed."""
    if str(need.get("type") or "") != "testcase":
        return None
    kind = str(need.get("verification_kind") or "")
    if kind not in VERIFICATION_KINDS:
        return None
    return kind, str(need.get("result") or "") == "passed"


def _record_revision_count(
    counts: list[int],
    pinned_revision: int,
    current_revision: int,
    *,
    passed: bool,
) -> None:
    """Update one current/outdated/predated evidence bucket."""
    if pinned_revision < current_revision:
        counts[2] += 1
        return
    if pinned_revision > current_revision:
        counts[3] += 1
        return
    counts[0] += 1
    if passed:
        counts[1] += 1


def _record_verification_need(
    need: Mapping[str, object],
    by_id: Mapping[str, Mapping[str, object]],
    totals: dict[str, dict[str, list[int]]],
) -> None:
    """Record currentness for all exact revision pins contributed by one testcase."""
    source = _verification_source(need)
    if source is None:
        return
    kind, passed = source
    for requirement_id, pinned_revision in revision_pinned_targets(need, "verifies"):
        requirement = by_id.get(requirement_id)
        current_revision = (
            requirement.get("revision") if requirement is not None else None
        )
        if not isinstance(current_revision, int):
            continue
        _record_revision_count(
            totals[requirement_id][kind],
            pinned_revision,
            current_revision,
            passed=passed,
        )


def verification_counts_from_needs(
    needs: list[Mapping[str, object]],
) -> dict[str, dict[str, EvidenceCounts]]:
    """Count current, outdated, and predated testcase evidence from one Needs graph."""
    by_id = {str(need["id"]): need for need in needs if need.get("id")}
    totals: dict[str, dict[str, list[int]]] = defaultdict(
        lambda: defaultdict(lambda: [0, 0, 0, 0])
    )
    for need in needs:
        _record_verification_need(need, by_id, totals)
    return {
        requirement_id: {
            kind: (counts[0], counts[1], counts[2], counts[3])
            for kind, counts in by_kind.items()
        }
        for requirement_id, by_kind in totals.items()
    }
