"""Shared proof indexing for human review projections over the Needs graph."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping

from ternforge_docops._internal.sphinx.review_common import (
    current_revision,
    need_sort_key,
)
from ternforge_docops._internal.sphinx.traceability import revision_pinned_targets

PROOF_ORDER = ("impl", "bdd", "unit", "property", "integration", "e2e")
PROOF_LABELS = {
    "impl": "Implementation",
    "bdd": "Behavior verification",
    "unit": "Unit verification",
    "property": "Property verification",
    "integration": "Integration verification",
    "e2e": "End-to-end verification",
}
_PROOF_TYPES = frozenset({"impl", "testcase"})


def proof_kind(item: Mapping[str, object]) -> str:
    """Return the authored evidence kind contributed by one graph node."""
    if str(item.get("type") or "") == "impl":
        return "impl"
    return str(item.get("verification_kind") or "verification")


def required_evidence_kinds(contract: Mapping[str, object]) -> tuple[str, ...]:
    """Normalize the authored required-evidence sequence without reordering it."""
    required = contract.get("required_evidence") or ()
    if isinstance(required, str):
        values = required.replace(";", ",").split(",")
    elif isinstance(required, list | tuple | set | frozenset):
        values = required
    else:
        return ()
    return tuple(
        dict.fromkeys(str(kind).strip() for kind in values if str(kind).strip())
    )


def ordered_proof_kinds(
    grouped: Mapping[str, list[Mapping[str, object]]],
    required: tuple[str, ...],
) -> list[str]:
    """Return known proof kinds first and custom kinds afterwards."""
    available = set(grouped) | set(required)
    ordered = [kind for kind in PROOF_ORDER if kind in available]
    ordered.extend(kind for kind in sorted(available) if kind not in ordered)
    return ordered


def current_proof_by_target(
    needs: Mapping[str, Mapping[str, object]],
) -> dict[str, list[Mapping[str, object]]]:
    """Index implementation and testcase evidence pinned to current revisions."""
    proof: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for need in needs.values():
        need_type = str(need.get("type") or "")
        if need_type not in _PROOF_TYPES:
            continue
        link_type = "implements" if need_type == "impl" else "verifies"
        for target_id, revision in revision_pinned_targets(need, link_type):
            if current_revision(needs, target_id, revision):
                proof[target_id].append(need)
    for values in proof.values():
        values.sort(key=need_sort_key)
    return proof
