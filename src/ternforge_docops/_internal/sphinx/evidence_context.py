"""Complementary evidence and scope-gap projection for verification narratives."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util.docutils import SphinxDirective
from sphinx_needs.api import get_needs_view

from ternforge_docops._internal.sphinx.proof_model import current_proof_by_target
from ternforge_docops._internal.sphinx.review_common import (
    bdd_scenario_url,
    human_test_title,
    verification_narrative_url,
)
from ternforge_docops._internal.verification.scope import (
    SCOPE_LABELS,
    SCOPE_ORDER,
    scope_rank,
)

if TYPE_CHECKING:
    from sphinx.application import Sphinx

_MAX_COMPLEMENTARY = 3


class _EvidenceContextNode(nodes.General, nodes.Element):
    """Placeholder resolved after imported testcase Needs exist."""


class _EvidenceContextDirective(SphinxDirective):
    """Render complementary proof and remaining observed scope for one claim."""

    has_content = False
    required_arguments = 1
    final_argument_whitespace = True
    option_spec = {"current-nodeids": directives.unchanged}  # noqa: RUF012

    def run(self) -> list[nodes.Node]:
        """Insert one graph-native complementary-evidence placeholder."""
        requirements = tuple(
            value.strip() for value in self.arguments[0].split(",") if value.strip()
        )
        nodeids = tuple(
            value.strip()
            for value in str(self.options.get("current-nodeids") or "").split(",")
            if value.strip()
        )
        node = _EvidenceContextNode()
        node["requirements"] = requirements
        node["nodeids"] = nodeids
        return [node]


def _proof(
    needs: Mapping[str, Mapping[str, object]],
    requirements: tuple[str, ...],
) -> list[Mapping[str, object]]:
    """Return current testcase proof for the selected contracts."""
    indexed = current_proof_by_target(needs)
    seen: set[str] = set()
    values: list[Mapping[str, object]] = []
    for requirement in requirements:
        for item in indexed.get(requirement, ()):
            if item.get("type") != "testcase":
                continue
            need_id = str(item.get("id") or "")
            if need_id and need_id not in seen:
                seen.add(need_id)
                values.append(item)
    return values


def _narrative_url(
    app: Sphinx,
    fromdocname: str,
    item: Mapping[str, object],
) -> str | None:
    """Resolve a testcase to its preferred human narrative."""
    if str(item.get("verification_kind") or "") == "bdd":
        return bdd_scenario_url(app, fromdocname, item)
    return verification_narrative_url(app, fromdocname, item)


def _current_scope(
    proof: list[Mapping[str, object]],
    nodeids: frozenset[str],
) -> int:
    """Return the widest scope occupied by the current narrative evidence."""
    return max(
        (
            scope_rank(item.get("scope_reach"))
            for item in proof
            if str(item.get("nodeid") or "") in nodeids
        ),
        default=-1,
    )


def _complementary_sort_key(
    item: Mapping[str, object],
    current_rank: int,
) -> tuple[bool, int, str, str]:
    """Prefer wider-scope evidence, then keep deterministic verification ordering."""
    rank = scope_rank(item.get("scope_reach"))
    return (
        rank <= current_rank,
        -rank,
        str(item.get("verification_kind") or ""),
        str(item.get("title") or ""),
    )


def _proof_signature(item: Mapping[str, object]) -> tuple[str, str]:
    """Collapse duplicate verification-kind/scope combinations."""
    return (
        str(item.get("verification_kind") or ""),
        str(item.get("scope_reach") or ""),
    )


def _distinct_candidates(
    candidates: list[Mapping[str, object]],
) -> list[Mapping[str, object]]:
    """Return the first distinct complementary evidence records."""
    selected: list[Mapping[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for item in candidates:
        signature = _proof_signature(item)
        if signature in seen:
            continue
        seen.add(signature)
        selected.append(item)
        if len(selected) == _MAX_COMPLEMENTARY:
            break
    return selected


def _complementary(
    proof: list[Mapping[str, object]],
    nodeids: frozenset[str],
) -> list[Mapping[str, object]]:
    """Pick at most three distinct complementary executions, widest scope first."""
    current_rank = _current_scope(proof, nodeids)
    candidates = [
        item for item in proof if str(item.get("nodeid") or "") not in nodeids
    ]
    candidates.sort(key=lambda item: _complementary_sort_key(item, current_rank))
    return _distinct_candidates(candidates)


def _covered_elsewhere(
    app: Sphinx,
    fromdocname: str,
    proof: list[Mapping[str, object]],
    nodeids: frozenset[str],
) -> nodes.paragraph:
    """Render concise links to complementary evidence or an explicit absence."""
    paragraph = nodes.paragraph()
    complementary = _complementary(proof, nodeids)
    if not complementary:
        paragraph += nodes.strong(text="No complementary evidence linked.")
        return paragraph

    paragraph += nodes.strong(text="Covered elsewhere: ")
    for index, item in enumerate(complementary):
        if index:
            paragraph += nodes.Text(" · ")
        label = human_test_title(item.get("title"))
        scope = SCOPE_LABELS.get(
            str(item.get("scope_reach") or ""),
            str(item.get("scope_reach") or "scope not captured"),
        )
        target = _narrative_url(app, fromdocname, item)
        if target is None:
            paragraph += nodes.Text(f"{label} ({scope})")
        else:
            paragraph += nodes.reference("", f"{label} ({scope})", refuri=target)
    return paragraph


def _remaining_gap(proof: list[Mapping[str, object]]) -> nodes.paragraph:
    """Render the broadest observed scope and the next unobserved external rung."""
    widest = max((scope_rank(item.get("scope_reach")) for item in proof), default=-1)
    paragraph = nodes.paragraph()
    paragraph += nodes.strong(text="Remaining gap: ")
    if widest >= scope_rank("live_external_reality"):
        paragraph += nodes.Text(
            "direct live external reality is retained; individual evidence "
            "limits still apply."
        )
        return paragraph
    label = SCOPE_LABELS.get(
        SCOPE_ORDER[widest] if widest >= 0 else "",
        "no captured verification scope",
    )
    paragraph += nodes.Text(
        f"broadest retained evidence reaches {label}; no direct live external "
        "interaction is retained for this claim."
    )
    return paragraph


def _replace_evidence_context(
    app: Sphinx,
    doctree: nodes.document,
    fromdocname: str,
) -> None:
    """Resolve complementary proof from the complete authoritative Needs graph."""
    needs = {
        str(need["id"]): need for need in get_needs_view(app).values() if need.get("id")
    }
    for node in list(doctree.findall(_EvidenceContextNode)):
        requirements = tuple(str(value) for value in node.get("requirements", ()))
        nodeids = frozenset(str(value) for value in node.get("nodeids", ()))
        proof = _proof(needs, requirements)
        replacement: list[nodes.Node] = [
            _covered_elsewhere(app, fromdocname, proof, nodeids),
            _remaining_gap(proof),
        ]
        node.replace_self(replacement)


def register_evidence_context(app: Sphinx) -> None:
    """Register graph-native complementary-evidence narrative projection."""
    app.add_node(_EvidenceContextNode)
    app.add_directive("ternforge-evidence-context", _EvidenceContextDirective)
    app.connect("doctree-resolved", _replace_evidence_context)
