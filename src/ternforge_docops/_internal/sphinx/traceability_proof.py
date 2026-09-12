"""Proof branches rendered inside the document-like traceability reader."""

from __future__ import annotations

import html
from collections import defaultdict
from collections.abc import Mapping

from ternforge_docops._internal.sphinx.proof_model import (
    PROOF_LABELS as _PROOF_LABELS,
    ordered_proof_kinds as _ordered_proof_kinds,
    proof_kind as _proof_kind,
    required_evidence_kinds as _required_evidence_kinds,
)
from ternforge_docops._internal.sphinx.review_common import (
    bdd_scenario_url,
    content_fields,
    human_test_title,
    need_url,
    verification_narrative_url,
)
from ternforge_docops._internal.sphinx.traceability_context import (
    ReaderContext,
    compact_need_link,
)


def _proof_groups(
    context: ReaderContext,
    contract: Mapping[str, object],
) -> list[tuple[str, str, list[Mapping[str, object]], bool]]:
    """Return proof groups in stable human reading order."""
    grouped: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for item in context.proof.get(str(contract["id"]), []):
        grouped[_proof_kind(item)].append(item)
    required = _required_evidence_kinds(contract)
    return [
        (
            kind,
            _PROOF_LABELS.get(kind, kind.replace("_", " ").title()),
            grouped.get(kind, []),
            kind in required,
        )
        for kind in _ordered_proof_kinds(grouped, required)
    ]


def _display_proof_items(
    kind: str,
    items: list[Mapping[str, object]],
) -> list[Mapping[str, object]]:
    """Deduplicate BDD executions to one human scenario entry."""
    if kind != "bdd":
        return items
    unique: dict[tuple[str, str], Mapping[str, object]] = {}
    for item in items:
        key = (
            str(item.get("gherkin_feature") or item.get("id") or ""),
            str(item.get("gherkin_scenario") or item.get("id") or ""),
        )
        unique.setdefault(key, item)
    return list(unique.values())


def _proof_count_text(
    kind: str,
    items: list[Mapping[str, object]],
    display_items: list[Mapping[str, object]],
    *,
    missing: bool,
) -> str:
    """Render a compact quantity label for one proof group."""
    if missing:
        return "Missing"
    if kind == "impl":
        count, noun = len(items), "location"
    elif kind == "bdd":
        count, noun = len(display_items), "scenario"
    else:
        count, noun = len(items), "check"
    return f"{count} {noun}" + ("" if count == 1 else "s")


def _proof_item_title_target(
    context: ReaderContext,
    kind: str,
    item: Mapping[str, object],
) -> tuple[str, str]:
    """Return the human title and preferred drill-down target for one proof item."""
    if kind == "bdd":
        title = str(item.get("gherkin_scenario") or human_test_title(item.get("title")))
        target = bdd_scenario_url(context.app, context.fromdocname, item)
        return title, target
    is_testcase = str(item.get("type") or "") == "testcase"
    title = (
        human_test_title(item.get("title"))
        if is_testcase
        else str(item.get("title") or item.get("id"))
    )
    target = (
        verification_narrative_url(context.app, context.fromdocname, item)
        if is_testcase
        else ""
    )
    return title, target


def _proof_details(
    context: ReaderContext,
    kind: str,
    display_items: list[Mapping[str, object]],
    count_text: str,
) -> str:
    """Render proof links when available, otherwise the compact count."""
    if not display_items:
        return f'<div class="ternforge-trace-count">{html.escape(count_text)}</div>'
    links: list[str] = []
    for item in display_items:
        title, target = _proof_item_title_target(context, kind, item)
        url = html.escape(target or need_url(context.app, context.fromdocname, item))
        links.append(f'<li><a href="{url}">{html.escape(title)}</a></li>')
    return (
        '<details class="ternforge-trace-secondary">'
        f"<summary>{html.escape(count_text)}</summary>"
        f"<ul>{''.join(links)}</ul>"
        "</details>"
    )


def _proof_group_card(
    context: ReaderContext,
    kind: str,
    label: str,
    items: list[Mapping[str, object]],
    *,
    required: bool,
) -> str:
    """Render one compact evidence branch."""
    display_items = _display_proof_items(kind, items)
    missing = required and not items
    state = "is-missing" if missing else "is-present"
    count_text = _proof_count_text(
        kind,
        items,
        display_items,
        missing=missing,
    )
    details = _proof_details(context, kind, display_items, count_text)
    return (
        f'<div class="ternforge-trace-card ternforge-trace-child-card {state}">'
        f'<div class="ternforge-trace-kind">{html.escape(label)}</div>'
        f"{details}"
        "</div>"
    )


def proof_inside_contract(
    context: ReaderContext,
    contract: Mapping[str, object],
) -> str:
    """Render implementation and verification inside the contract card."""
    proof = "".join(
        _proof_group_card(
            context,
            kind,
            label,
            items,
            required=required,
        )
        for kind, label, items, required in _proof_groups(context, contract)
    )
    if not proof:
        return ""
    return f'<div class="ternforge-trace-nested-proof">{proof}</div>'


def _constraint_child(
    context: ReaderContext,
    constraint: Mapping[str, object],
    number: str,
) -> str:
    """Render one technical requirement and its compact evidence."""
    fields = content_fields(constraint.get("content"))
    primary = fields.get("Constraint", fields.get("Summary", ""))
    proof = "".join(
        _proof_group_card(
            context,
            kind,
            label,
            items,
            required=required,
        )
        for kind, label, items, required in _proof_groups(context, constraint)
    )
    summary = f"<p>{html.escape(primary)}</p>" if primary else ""
    nested = f'<div class="ternforge-trace-nested-proof">{proof}</div>' if proof else ""
    return (
        '<div class="ternforge-trace-branch-item">'
        '<div class="ternforge-trace-card ternforge-trace-child-card '
        'ternforge-trace-rule-card">'
        '<div class="ternforge-trace-heading">'
        f'<span class="ternforge-trace-number">{html.escape(number)}</span>'
        '<span class="ternforge-trace-kind">Technical requirement</span>'
        "</div>"
        f"<strong>{compact_need_link(context, constraint)}</strong>"
        f"{summary}"
        f"{nested}"
        "</div></div>"
    )


def trace_children(
    context: ReaderContext,
    requirement: Mapping[str, object],
    number: str,
) -> str:
    """Render only semantic child rules; proof stays inside contract cards."""
    requirement_id = str(requirement["id"])
    children = [
        _constraint_child(
            context,
            constraint,
            f"{number}.{chr(ord('a') + index)}",
        )
        for index, constraint in enumerate(
            context.constraints_by_req.get(requirement_id, [])
        )
    ]
    if not children:
        return ""
    return (
        '<div class="ternforge-trace-side ternforge-trace-children">'
        '<div class="ternforge-trace-branch">'
        f"{''.join(children)}"
        "</div></div>"
    )
