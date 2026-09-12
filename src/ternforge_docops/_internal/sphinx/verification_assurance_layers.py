"""Scope and evidence-trust layers for the verification assurance map."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Protocol

from docutils import nodes

from ternforge_docops._internal.sphinx.evidence_trust import producer_trust_url
from ternforge_docops._internal.sphinx.review_common import (
    bdd_scenario_url,
    human_test_title,
    need_url,
    normalize_ids,
    verification_narrative_url,
)
from ternforge_docops._internal.verification.scope import SCOPE_LABELS, SCOPE_ORDER

if TYPE_CHECKING:
    from sphinx.application import Sphinx

_VERIFICATION_KINDS = ("bdd", "unit", "property", "integration", "e2e")


class AssuranceLayerContext(Protocol):
    """Context required by independently rendered assurance layers."""

    app: Sphinx
    fromdocname: str
    needs: Mapping[str, Mapping[str, object]]


def _layer_item(title: str, body: nodes.Node | list[nodes.Node]) -> nodes.list_item:
    """Build one ordered assurance layer."""
    item = nodes.list_item()
    paragraph = nodes.paragraph()
    paragraph += nodes.strong(text=f"{title}: ")
    if isinstance(body, list):
        item += paragraph
        item.extend(body)
    else:
        paragraph += body
        item += paragraph
    return item


def _runtime_url(
    context: AssuranceLayerContext,
    item: Mapping[str, object],
) -> str | None:
    """Resolve a testcase to its preferred human verification narrative."""
    if str(item.get("verification_kind") or "") == "bdd":
        return bdd_scenario_url(context.app, context.fromdocname, item)
    return verification_narrative_url(context.app, context.fromdocname, item)


def _test_reference(
    context: AssuranceLayerContext,
    item: Mapping[str, object],
) -> nodes.reference:
    """Build one testcase reference with a Needs fallback."""
    label = human_test_title(item.get("title"))
    target = _runtime_url(context, item)
    if target is not None:
        return nodes.reference("", label, refuri=target)
    return nodes.reference(
        "",
        label,
        refuri=need_url(context.app, context.fromdocname, item),
    )


def _scope_items(
    grouped: Mapping[str, list[Mapping[str, object]]],
) -> list[Mapping[str, object]]:
    """Flatten testcase proof with captured scope metadata."""
    return [
        item
        for kind in _VERIFICATION_KINDS
        for item in grouped.get(kind, [])
        if str(item.get("scope_reach") or "")
    ]


def _scope_entry(
    context: AssuranceLayerContext,
    items: list[Mapping[str, object]],
) -> nodes.entry:
    """Render one scope-ladder cell with concrete verification links."""
    entry = nodes.entry()
    if not items:
        entry += nodes.paragraph(text="—")
        return entry
    values = nodes.bullet_list()
    for item in items:
        row = nodes.list_item()
        paragraph = nodes.paragraph()
        paragraph += _test_reference(context, item)
        external = str(item.get("external_reach") or "")
        if external and external != "local":
            paragraph += nodes.Text(f" · {external}")
        row += paragraph
        values += row
    entry += values
    return entry


def verification_scope_layer(
    context: AssuranceLayerContext,
    grouped: Mapping[str, list[Mapping[str, object]]],
) -> nodes.list_item:
    """Render the ordered observed scope ladder without inferring from test kind."""
    proof = _scope_items(grouped)
    if not proof:
        return _layer_item(
            "Verification scope",
            nodes.paragraph(
                text="No execution evidence is retained for current proof."
            ),
        )

    table = nodes.table(classes=["docutils", "align-default"])
    tgroup = nodes.tgroup(cols=len(SCOPE_ORDER))
    table += tgroup
    for _ in SCOPE_ORDER:
        tgroup += nodes.colspec(colwidth=16)

    header = nodes.row()
    for scope in SCOPE_ORDER:
        entry = nodes.entry()
        entry += nodes.paragraph(text=SCOPE_LABELS[scope])
        header += entry
    thead = nodes.thead()
    thead += header
    tgroup += thead

    body_row = nodes.row()
    for scope in SCOPE_ORDER:
        body_row += _scope_entry(
            context,
            [item for item in proof if item.get("scope_reach") == scope],
        )
    tbody = nodes.tbody()
    tbody += body_row
    tgroup += tbody

    parts: list[nodes.Node] = [
        nodes.paragraph(
            text=(
                "Placement comes from retained runtime/coverage facts; verification "
                "kind does not choose the scope rung."
            )
        ),
        table,
    ]
    if not any(item.get("external_reach") == "direct" for item in proof):
        gap = nodes.paragraph()
        gap += nodes.strong(text="Live reality gap: ")
        gap += nodes.Text(
            "no retained execution captures a direct external interaction."
        )
        parts.append(gap)
    return _layer_item("Verification scope", parts)


def _producer_ids(
    grouped: Mapping[str, list[Mapping[str, object]]],
) -> tuple[str, ...]:
    """Return distinct producer IDs behind current verification proof."""
    return tuple(
        dict.fromkeys(
            producer_id
            for kind in _VERIFICATION_KINDS
            for item in grouped.get(kind, [])
            for producer_id in normalize_ids(item.get("produced_by"))
        )
    )


def _producer_item(
    context: AssuranceLayerContext,
    producer_id: str,
) -> nodes.list_item:
    """Render one graph-native producer link plus risk classification."""
    producer = context.needs.get(producer_id)
    item = nodes.list_item()
    paragraph = nodes.paragraph()
    label = (
        str(producer.get("title") or producer_id)
        if producer is not None
        else producer_id
    )
    paragraph += nodes.reference(
        "",
        label,
        refuri=producer_trust_url(context.app, context.fromdocname, producer_id),
    )
    if producer is not None:
        detail = " · ".join(
            value
            for value in (
                str(producer.get("producer_role") or ""),
                str(producer.get("producer_impact") or ""),
            )
            if value
        )
        if detail:
            paragraph += nodes.Text(f" — {detail}")
    item += paragraph
    return item


def evidence_trust_layer(
    context: AssuranceLayerContext,
    grouped: Mapping[str, list[Mapping[str, object]]],
) -> nodes.list_item:
    """Render TEST → producer links into the evidence-of-evidence route."""
    producer_ids = _producer_ids(grouped)
    if not producer_ids:
        return _layer_item(
            "Trust of evidence",
            nodes.paragraph(
                text=(
                    "No graph-native producer identities are retained for "
                    "current proof."
                )
            ),
        )

    values = nodes.bullet_list()
    for producer_id in producer_ids:
        values += _producer_item(context, producer_id)

    return _layer_item(
        "Trust of evidence",
        [
            nodes.paragraph(
                text=(
                    "Open a producer to inspect its trust basis, calibration or "
                    "independent verification, and residual doubt."
                )
            ),
            values,
        ],
    )
