"""Document-like traceability reader over the authoritative Needs graph."""

from __future__ import annotations

import html
from collections import defaultdict
from collections.abc import Mapping
from typing import TYPE_CHECKING

from ternforge_docops._internal.sphinx.review_common import (
    content_fields,
    current_revision,
    need_sort_key,
    need_url,
    normalize_ids,
    strip_inline_markup,
)
from ternforge_docops._internal.sphinx.traceability import revision_pinned_targets
from ternforge_docops._internal.sphinx.traceability_context import (
    ReaderContext as _ReaderContext,
    compact_need_link as _compact_need_link,
)
from ternforge_docops._internal.sphinx.traceability_proof import (
    proof_inside_contract as _proof_inside_contract,
    trace_children as _trace_children,
)

if TYPE_CHECKING:
    from sphinx.application import Sphinx

_PROOF_TYPES = frozenset({"impl", "testcase"})


def _proof_by_target(
    needs: Mapping[str, Mapping[str, object]],
) -> dict[str, list[Mapping[str, object]]]:
    """Index current implementation and verification evidence by contract."""
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


def _technical_details(need: Mapping[str, object]) -> str:
    """Render machine identity as secondary information, not card content."""
    need_id = html.escape(str(need["id"]))
    revision = need.get("revision")
    status = str(need.get("status") or "")
    metadata = [f"<code>{need_id}</code>"]
    if revision:
        metadata.append(f"revision {html.escape(str(revision))}")
    if status:
        metadata.append(html.escape(status))
    return (
        '<details class="ternforge-review-technical">'
        "<summary>IDs and revision</summary>"
        f"<p>{' · '.join(metadata)}</p>"
        "</details>"
    )


def _sort_hierarchy_children(
    *mappings: dict[str, list[Mapping[str, object]]],
) -> None:
    """Sort every authored hierarchy branch using the shared stable key."""
    for mapping in mappings:
        for children in mapping.values():
            children.sort(key=need_sort_key)


def _reader_hierarchy(
    needs: Mapping[str, Mapping[str, object]],
) -> tuple[
    list[Mapping[str, object]],
    dict[str, list[Mapping[str, object]]],
    dict[str, list[Mapping[str, object]]],
    dict[str, list[Mapping[str, object]]],
]:
    """Collect the authored hierarchy used by the document-like reader."""
    goals = sorted(
        (need for need in needs.values() if need.get("type") == "goal"),
        key=need_sort_key,
    )
    features_by_goal: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    reqs_by_feature: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    constraints_by_req: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    buckets = {
        "feature": features_by_goal,
        "req": reqs_by_feature,
        "treq": constraints_by_req,
    }

    for need in needs.values():
        parents = normalize_ids(need.get("derives"))
        bucket = buckets.get(str(need.get("type") or ""))
        if parents and bucket is not None:
            bucket[parents[0]].append(need)

    _sort_hierarchy_children(features_by_goal, reqs_by_feature, constraints_by_req)
    return goals, features_by_goal, reqs_by_feature, constraints_by_req


def _hierarchy_card(
    context: _ReaderContext,
    need: Mapping[str, object],
    kind: str,
    number: str,
    *,
    summary: bool,
) -> str:
    """Render one numbered Goal/Capability card exactly once."""
    prose = ""
    if summary:
        text = strip_inline_markup(str(need.get("content") or ""))
        if text:
            prose = f"<p>{html.escape(text)}</p>"
    return (
        '<div class="ternforge-trace-card ternforge-hierarchy-card">'
        '<div class="ternforge-trace-heading">'
        f'<span class="ternforge-trace-number">{html.escape(number)}</span>'
        f'<span class="ternforge-trace-kind">{html.escape(kind)}</span>'
        "</div>"
        f"<strong>{_compact_need_link(context, need)}</strong>"
        f"{prose}"
        "</div>"
    )


def _trace_current(
    context: _ReaderContext,
    requirement: Mapping[str, object],
    number: str,
) -> str:
    """Render the central human-readable requirement card."""
    fields = content_fields(requirement.get("content"))
    title = html.escape(str(requirement.get("title") or requirement["id"]))
    canonical = html.escape(need_url(context.app, context.fromdocname, requirement))
    primary = fields.get("Statement", fields.get("Summary", ""))
    rationale = fields.get("Rationale", "")
    verification = fields.get("Verification intent", "")
    body = [
        '<div class="ternforge-trace-card ternforge-trace-current">',
        '<div class="ternforge-trace-heading">',
        f'<span class="ternforge-trace-number">{html.escape(number)}</span>',
        '<span class="ternforge-trace-kind">Requirement</span>',
        "</div>",
        f'<h4><a href="{canonical}">{title}</a></h4>',
    ]
    if primary:
        body.append(f'<p class="ternforge-trace-statement">{html.escape(primary)}</p>')
    if rationale or verification:
        context_parts = [
            '<details class="ternforge-trace-secondary">',
            "<summary>Why and verification</summary>",
        ]
        if rationale:
            context_parts.append(
                f"<p><strong>Why:</strong> {html.escape(rationale)}</p>"
            )
        if verification:
            context_parts.append(
                f"<p><strong>How verified:</strong> {html.escape(verification)}</p>"
            )
        context_parts.append("</details>")
        body.extend(context_parts)
    proof = _proof_inside_contract(context, requirement)
    if proof:
        body.append(proof)
    body.extend((_technical_details(requirement), "</div>"))
    return "".join(body)


def _requirement_html(
    context: _ReaderContext,
    requirement: Mapping[str, object],
    number: str,
) -> str:
    """Render one numbered requirement with proof branching to the right."""
    return (
        '<article class="ternforge-requirement-flow">'
        '<div class="ternforge-requirement-connector" aria-hidden="true"></div>'
        f"{_trace_current(context, requirement, number)}"
        f"{_trace_children(context, requirement, number)}"
        "</article>"
    )


def _feature_html(
    context: _ReaderContext,
    feature: Mapping[str, object],
    reqs: list[Mapping[str, object]],
    goal_index: int,
    feature_index: int,
) -> str:
    """Render one numbered capability once, then its requirement staircase."""
    feature_number = f"{goal_index}.{feature_index}"
    feature_card = _hierarchy_card(
        context,
        feature,
        "Capability",
        feature_number,
        summary=True,
    )
    requirements = "".join(
        _requirement_html(
            context,
            requirement,
            f"{feature_number}.{requirement_index}",
        )
        for requirement_index, requirement in enumerate(reqs, start=1)
    )
    feature_id = html.escape(str(feature["id"]))
    return (
        '<section class="ternforge-review-feature" '
        f'id="review-{feature_id}">'
        '<div class="ternforge-feature-connector" aria-hidden="true"></div>'
        f"{feature_card}"
        '<div class="ternforge-requirement-list">'
        f"{requirements}"
        "</div></section>"
    )


def _goal_html(
    context: _ReaderContext,
    goal: Mapping[str, object],
    features: list[Mapping[str, object]],
    goal_index: int,
) -> str:
    """Render a goal once with capabilities and requirements as a staircase."""
    goal_id = str(goal["id"])
    goal_card = _hierarchy_card(
        context,
        goal,
        "Goal",
        str(goal_index),
        summary=True,
    )
    feature_blocks = "".join(
        _feature_html(
            context,
            feature,
            context.reqs_by_feature.get(str(feature["id"]), []),
            goal_index,
            feature_index,
        )
        for feature_index, feature in enumerate(features, start=1)
    )
    return (
        f'<section class="ternforge-review-goal" id="review-{html.escape(goal_id)}">'
        f"{goal_card}"
        '<div class="ternforge-feature-list">'
        f"{feature_blocks}"
        "</div></section>"
    )


def _reader_navigation(
    goals: list[Mapping[str, object]],
    features_by_goal: Mapping[str, list[Mapping[str, object]]],
) -> str:
    """Render a collapsible Goal -> Capability navigation sidebar."""
    goal_items: list[str] = []
    for goal_index, goal in enumerate(goals, start=1):
        goal_id = html.escape(str(goal["id"]))
        goal_title = html.escape(str(goal.get("title") or goal["id"]))
        feature_items: list[str] = []
        for feature_index, feature in enumerate(
            features_by_goal.get(str(goal["id"]), []),
            start=1,
        ):
            feature_id = html.escape(str(feature["id"]))
            feature_title = html.escape(str(feature.get("title") or feature["id"]))
            feature_items.append(
                '<li class="ternforge-review-nav-feature">'
                f'<a href="#review-{feature_id}">'
                f"<span>{goal_index}.{feature_index}</span>{feature_title}</a>"
                "</li>"
            )
        features = (
            f'<ol class="ternforge-review-nav-features">{"".join(feature_items)}</ol>'
            if feature_items
            else ""
        )
        goal_items.append(
            '<li class="ternforge-review-nav-goal">'
            f'<a href="#review-{goal_id}">'
            f"<span>{goal_index}</span>{goal_title}</a>"
            f"{features}</li>"
        )
    return (
        '<details class="ternforge-review-navigation" open>'
        '<summary aria-label="Toggle goals and capabilities navigation">'
        '<span class="ternforge-review-nav-toggle" aria-hidden="true"></span>'
        '<span class="ternforge-review-nav-title">Goals &amp; capabilities</span>'
        "</summary>"
        '<nav aria-label="Goals and capabilities">'
        f'<ol class="ternforge-review-nav-goals">{"".join(goal_items)}</ol>'
        "</nav></details>"
    )


def reader_html(
    app: Sphinx,
    fromdocname: str,
    needs: Mapping[str, Mapping[str, object]],
) -> str:
    """Render the specification as independent StrictDoc-style HTML flows."""
    goals, features_by_goal, reqs_by_feature, constraints_by_req = _reader_hierarchy(
        needs
    )
    context = _ReaderContext(
        app=app,
        fromdocname=fromdocname,
        proof=_proof_by_target(needs),
        reqs_by_feature=reqs_by_feature,
        constraints_by_req=constraints_by_req,
    )
    chunks = [
        '<div class="ternforge-review-layout">',
        _reader_navigation(goals, features_by_goal),
        '<div class="ternforge-traceability-reader">',
        (
            '<div class="ternforge-trace-reading-order">'
            "<span>Why this exists</span><i>→</i>"
            "<span>What must be true</span><i>→</i>"
            "<span>What proves it now</span>"
            "</div>"
        ),
    ]
    chunks.extend(
        _goal_html(
            context,
            goal,
            features_by_goal.get(str(goal["id"]), []),
            goal_index,
        )
        for goal_index, goal in enumerate(goals, start=1)
    )
    chunks.extend(("</div>", "</div>"))
    return "".join(chunks)
