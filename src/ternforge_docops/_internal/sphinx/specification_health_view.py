"""Stock Sphinx presentation for derived specification health."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from docutils import nodes
from sphinx.util.docutils import SphinxDirective
from sphinx_needs.api import get_needs_view

from ternforge_docops._internal.sphinx.specification_health import (
    SpecificationHealth,
    project_specification_health,
)

if TYPE_CHECKING:
    from sphinx.application import Sphinx


class _SpecificationHealthNode(nodes.General, nodes.Element):
    """Placeholder resolved once the complete Needs graph is available."""


class _SpecificationHealthDirective(SphinxDirective):
    """Render recursive specification health from the authoritative Needs graph."""

    has_content = False

    def run(self) -> list[nodes.Node]:
        """Insert a late-bound specification-health placeholder."""
        return [_SpecificationHealthNode()]


def _entry(text: str, *, header: bool = False) -> nodes.entry:
    """Build one stock docutils table entry."""
    entry = nodes.entry()
    if header:
        entry["classes"].append("head")
    entry += nodes.paragraph(text=text)
    return entry


def _ratio(covered: int, total: int) -> str:
    """Render an honest numerator/denominator without inventing a combined score."""
    return f"{covered}/{total}"


def _summary_values(
    health: Mapping[str, SpecificationHealth],
    need_type: str,
) -> tuple[str, str, str]:
    """Return structure, direct-evidence, and deep ratios for one graph layer."""
    states = [state for state in health.values() if state.need_type == need_type]
    total = len(states)
    structural = _ratio(sum(state.structural_covered for state in states), total)
    deep = _ratio(sum(state.deep_covered for state in states), total)
    evidence_states = [
        state for state in states if state.direct_evidence_covered is not None
    ]
    if not evidence_states:
        return structural, "—", deep
    evidence = _ratio(
        sum(bool(state.direct_evidence_covered) for state in evidence_states),
        len(evidence_states),
    )
    return structural, evidence, deep


def _summary_table(health: Mapping[str, SpecificationHealth]) -> nodes.table:
    """Render layer-by-layer structural, evidence, and deep coverage."""
    table = nodes.table(classes=["docutils", "align-default"])
    tgroup = nodes.tgroup(cols=4)
    table += tgroup
    for width in (34, 22, 22, 22):
        tgroup += nodes.colspec(colwidth=width)

    thead = nodes.thead()
    header = nodes.row()
    for title in ("Layer", "Structure", "Direct evidence", "Deep coverage"):
        header += _entry(title, header=True)
    thead += header
    tgroup += thead

    labels = (
        ("goal", "Goals"),
        ("feature", "Capabilities"),
        ("req", "Requirements"),
        ("treq", "Technical requirements"),
    )
    tbody = nodes.tbody()
    for need_type, label in labels:
        structural, evidence, deep = _summary_values(health, need_type)
        row = nodes.row()
        row += _entry(label)
        row += _entry(structural)
        row += _entry(evidence)
        row += _entry(deep)
        tbody += row
    tgroup += tbody
    return table


def _need_reference(
    app: Sphinx,
    fromdocname: str,
    need: Mapping[str, object],
) -> nodes.reference:
    """Build a stock internal link to an existing authored Need."""
    need_id = str(need["id"])
    target_doc = str(need.get("docname") or fromdocname)
    uri = app.builder.get_relative_uri(fromdocname, target_doc)
    return nodes.reference("", need_id, refuri=f"{uri}#{need_id}")


def _action_text(state: SpecificationHealth) -> str:
    """Describe one deep-coverage gap as a compact action-oriented sentence."""
    parts: list[str] = []
    if state.gap_reason:
        parts.append(state.gap_reason)
    if state.missing_evidence:
        parts.append(f"Missing evidence: {', '.join(state.missing_evidence)}")
    if state.blocked_by:
        parts.append(f"Blocked by: {', '.join(state.blocked_by)}")
    return ". ".join(parts) or "Deep coverage incomplete"


def _actionable_states(
    health: Mapping[str, SpecificationHealth],
) -> tuple[SpecificationHealth, ...]:
    """Return direct root causes without duplicating their affected ancestors."""
    return tuple(
        sorted(
            (
                state
                for state in health.values()
                if state.gap_reason or state.missing_evidence
            ),
            key=lambda state: (state.need_type, state.need_id),
        )
    )


def _action_table(
    app: Sphinx,
    fromdocname: str,
    health: Mapping[str, SpecificationHealth],
    needs: Mapping[str, Mapping[str, object]],
) -> nodes.table | nodes.paragraph:
    """Render only actionable root causes; deep impact remains in the summary."""
    gaps = _actionable_states(health)
    if not gaps:
        return nodes.paragraph(text="No active specification coverage gaps.")

    table = nodes.table(classes=["docutils", "align-default"])
    tgroup = nodes.tgroup(cols=3)
    table += tgroup
    for width in (28, 16, 56):
        tgroup += nodes.colspec(colwidth=width)
    thead = nodes.thead()
    header = nodes.row()
    for title in ("Need", "Layer", "Action required"):
        header += _entry(title, header=True)
    thead += header
    tgroup += thead

    tbody = nodes.tbody()
    for state in gaps:
        row = nodes.row()
        need_entry = nodes.entry()
        paragraph = nodes.paragraph()
        need = needs.get(state.need_id)
        if need is None:
            paragraph += nodes.Text(state.need_id)
        else:
            paragraph += _need_reference(app, fromdocname, need)
        need_entry += paragraph
        row += need_entry
        row += _entry(state.need_type.upper())
        row += _entry(_action_text(state))
        tbody += row
    tgroup += tbody
    return table


def _replace_health_nodes(
    app: Sphinx,
    doctree: nodes.document,
    fromdocname: str,
) -> None:
    """Resolve specification-health placeholders from the complete Needs graph."""
    view = get_needs_view(app)
    needs = {str(need["id"]): need for need in view.values() if need.get("id")}
    health = project_specification_health(needs.values())
    for node in list(doctree.findall(_SpecificationHealthNode)):
        replacement: list[nodes.Node] = []
        replacement.append(nodes.rubric(text="What needs attention"))
        replacement.append(_action_table(app, fromdocname, health, needs))
        replacement.append(nodes.rubric(text="Audit totals"))
        replacement.append(_summary_table(health))
        node.replace_self(replacement)


def register_specification_health_view(app: Sphinx) -> None:
    """Register the stock Sphinx presentation for recursive specification health."""
    app.add_node(_SpecificationHealthNode)
    app.add_directive("ternforge-specification-health", _SpecificationHealthDirective)
    app.connect("doctree-resolved", _replace_health_nodes)
