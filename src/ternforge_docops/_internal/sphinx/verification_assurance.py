"""Layered verification-assurance projection over retained engineering proof."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from docutils import nodes
from sphinx.util.docutils import SphinxDirective
from sphinx_needs.api import get_needs_view

from ternforge_docops._internal.sphinx.proof_model import current_proof_by_target
from ternforge_docops._internal.sphinx.review_common import need_sort_key
from ternforge_docops._internal.sphinx.revision_evidence import (
    verification_counts_from_needs,
)
from ternforge_docops._internal.sphinx.specification_health import (
    project_specification_health,
)
from ternforge_docops._internal.sphinx.verification_assurance_render import (
    AssuranceRenderContext,
    contract_section,
)

if TYPE_CHECKING:
    from sphinx.application import Sphinx

_ACTIVE_STATUS = "accepted"
_CONTRACT_TYPES = ("req", "treq")


class _VerificationAssuranceNode(nodes.General, nodes.Element):
    """Placeholder resolved after the complete Needs graph is available."""


class VerificationAssuranceDirective(SphinxDirective):
    """Render a layered contract-to-runtime assurance reading path."""

    has_content = False

    def run(self) -> list[nodes.Node]:
        """Insert one late-bound assurance placeholder."""
        return [_VerificationAssuranceNode()]


def _contract_needs(
    needs: Mapping[str, Mapping[str, object]],
) -> list[Mapping[str, object]]:
    """Select accepted Requirements and Technical requirements in authored order."""
    return sorted(
        (
            need
            for need in needs.values()
            if str(need.get("type") or "") in _CONTRACT_TYPES
            and str(need.get("status") or "") == _ACTIVE_STATUS
        ),
        key=need_sort_key,
    )


def assurance_nodes(
    app: Sphinx,
    fromdocname: str,
    needs: Mapping[str, Mapping[str, object]],
) -> list[nodes.Node]:
    """Project layered proof from the authoritative graph and retained drill-downs."""
    items = list(needs.values())
    health = project_specification_health(items)
    proof = current_proof_by_target(needs)
    counts = verification_counts_from_needs(items)
    contracts = _contract_needs(needs)
    if not contracts:
        message = "No accepted Requirements or Technical requirements found."
        return [nodes.paragraph(text=message)]

    context = AssuranceRenderContext(app=app, fromdocname=fromdocname)
    result: list[nodes.Node] = []
    for contract in contracts:
        contract_id = str(contract["id"])
        contract_health = health.get(contract_id)
        if contract_health is None:
            continue
        result.append(
            contract_section(
                context,
                contract,
                contract_health,
                proof.get(contract_id, []),
                counts.get(contract_id, {}),
            )
        )
    return result or [nodes.paragraph(text="No active assurance contracts found.")]


def replace_verification_assurance_nodes(
    app: Sphinx,
    doctree: nodes.document,
    fromdocname: str,
) -> None:
    """Resolve assurance placeholders after the complete Needs graph is available."""
    view = get_needs_view(app)
    needs = {str(need["id"]): need for need in view.values() if need.get("id")}
    for node in list(doctree.findall(_VerificationAssuranceNode)):
        node.replace_self(assurance_nodes(app, fromdocname, needs))


def register_verification_assurance_view(app: Sphinx) -> None:
    """Register the layered verification-assurance projection."""
    app.add_node(_VerificationAssuranceNode)
    app.add_directive(
        "ternforge-verification-assurance-map",
        VerificationAssuranceDirective,
    )
    app.connect("doctree-resolved", replace_verification_assurance_nodes)
