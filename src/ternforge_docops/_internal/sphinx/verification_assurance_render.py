"""Theme-native rendering for the layered verification-assurance map."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from docutils import nodes

from ternforge_docops._internal.sphinx.proof_model import (
    PROOF_LABELS,
    proof_kind,
    required_evidence_kinds,
)
from ternforge_docops._internal.sphinx.review_common import (
    bdd_scenario_url,
    human_test_title,
    need_url,
    verification_narrative_url,
)
from ternforge_docops._internal.sphinx.revision_evidence import EvidenceCounts
from ternforge_docops._internal.sphinx.specification_health import SpecificationHealth

if TYPE_CHECKING:
    from sphinx.application import Sphinx

_VERIFICATION_KINDS = ("bdd", "unit", "property", "integration", "e2e")


@dataclass(frozen=True)
class AssuranceRenderContext:
    """Sphinx context needed to build links without copying proof data."""

    app: Sphinx
    fromdocname: str


def _reference(
    context: AssuranceRenderContext,
    need: Mapping[str, object],
    *,
    label: str | None = None,
) -> nodes.reference:
    """Build one link to an existing Need without copying its content."""
    text = label or str(need.get("title") or need.get("id") or "Need")
    return nodes.reference(
        "",
        text,
        refuri=need_url(context.app, context.fromdocname, need),
    )


def _runtime_url(
    context: AssuranceRenderContext,
    item: Mapping[str, object],
) -> str | None:
    """Resolve the preferred human runtime-assurance drill-down."""
    kind = str(item.get("verification_kind") or "")
    if kind == "bdd":
        return bdd_scenario_url(context.app, context.fromdocname, item)
    return verification_narrative_url(context.app, context.fromdocname, item)


def _test_reference(
    context: AssuranceRenderContext,
    item: Mapping[str, object],
) -> nodes.reference:
    """Build one testcase link to its narrative when available."""
    title = human_test_title(item.get("title"))
    target = _runtime_url(context, item)
    if target is None:
        return _reference(context, item, label=title)
    return nodes.reference("", title, refuri=target)


def _proof_groups(
    proof: list[Mapping[str, object]],
) -> dict[str, list[Mapping[str, object]]]:
    """Group current proof by authored evidence kind."""
    grouped: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for item in proof:
        grouped[proof_kind(item)].append(item)
    return grouped


def _required_summary(contract: Mapping[str, object]) -> str:
    """Render the authored required-evidence contract compactly."""
    required = required_evidence_kinds(contract)
    return ", ".join(required) if required else "none declared"


def _layer_item(title: str, body: nodes.Node | list[nodes.Node]) -> nodes.list_item:
    """Build one ordered proof layer with a bold heading."""
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


def _contract_layer(contract: Mapping[str, object]) -> nodes.list_item:
    """Describe the authored contract identity and proof obligation."""
    revision = contract.get("revision")
    status = str(contract.get("status") or "")
    detail = (
        "Current authored contract"
        + (f", revision {revision}" if revision is not None else "")
        + (f", status {status}" if status else "")
        + f". Required evidence: {_required_summary(contract)}."
    )
    return _layer_item("Contract", nodes.paragraph(text=detail))


def _proof_links(
    context: AssuranceRenderContext,
    items: list[Mapping[str, object]],
    *,
    tests: bool,
) -> nodes.bullet_list:
    """Render concrete current proof links with native list semantics."""
    result = nodes.bullet_list()
    for proof in items:
        entry = nodes.list_item()
        paragraph = nodes.paragraph()
        paragraph += (
            _test_reference(context, proof) if tests else _reference(context, proof)
        )
        outcome = str(proof.get("result") or "") if tests else ""
        if outcome:
            paragraph += nodes.Text(f" — {outcome}")
        entry += paragraph
        result += entry
    return result


def _implementation_layer(
    context: AssuranceRenderContext,
    contract: Mapping[str, object],
    grouped: Mapping[str, list[Mapping[str, object]]],
) -> nodes.list_item:
    """Render current implementation loci or an explicit gap."""
    implementations = grouped.get("impl", [])
    required = "impl" in required_evidence_kinds(contract)
    if not implementations:
        detail = (
            "Missing required current implementation evidence."
            if required
            else "No implementation evidence is required for this contract."
        )
        return _layer_item("Implementation", nodes.paragraph(text=detail))
    noun = "location" if len(implementations) == 1 else "locations"
    return _layer_item(
        "Implementation",
        [
            nodes.paragraph(
                text=f"{len(implementations)} current implementation {noun}."
            ),
            _proof_links(context, implementations, tests=False),
        ],
    )


def _count_summary(counts: EvidenceCounts | None) -> str:
    """Render current pass/fail plus stale revision evidence without ambiguity."""
    if counts is None:
        return "no execution evidence"
    total, passed, outdated, predated = counts
    parts = [f"{passed}/{total} current passed"] if total else ["no current execution"]
    if outdated:
        parts.append(f"{outdated} outdated")
    if predated:
        parts.append(f"{predated} predated")
    return "; ".join(parts)


def _kind_status(
    kind: str,
    counts: EvidenceCounts | None,
    *,
    required: bool,
) -> nodes.paragraph:
    """Build one verification-kind status line."""
    paragraph = nodes.paragraph()
    label = PROOF_LABELS.get(kind, kind.replace("_", " ").title())
    paragraph += nodes.strong(text=f"{label}: ")
    paragraph += nodes.Text(_count_summary(counts))
    paragraph += nodes.Text(" · required" if required else " · complementary")
    return paragraph


def _verification_detail(
    context: AssuranceRenderContext,
    kind: str,
    items: list[Mapping[str, object]],
    counts: EvidenceCounts | None,
    *,
    required: bool,
) -> nodes.list_item:
    """Render one verification layer plus links to concrete executions."""
    entry = nodes.list_item()
    entry += _kind_status(kind, counts, required=required)
    if items:
        entry += _proof_links(context, items, tests=True)
    return entry


def _verification_layer(
    context: AssuranceRenderContext,
    contract: Mapping[str, object],
    grouped: Mapping[str, list[Mapping[str, object]]],
    counts: Mapping[str, EvidenceCounts],
) -> nodes.list_item:
    """Render requested and complementary verification layers."""
    required = set(required_evidence_kinds(contract))
    visible = [
        kind
        for kind in _VERIFICATION_KINDS
        if kind in required or kind in grouped or kind in counts
    ]
    if not visible:
        return _layer_item(
            "Verification",
            nodes.paragraph(text="No verification layers are declared or retained."),
        )
    details = nodes.bullet_list()
    for kind in visible:
        details += _verification_detail(
            context,
            kind,
            grouped.get(kind, []),
            counts.get(kind),
            required=kind in required,
        )
    return _layer_item("Verification", [details])


def _assurance_links(
    context: AssuranceRenderContext,
    grouped: Mapping[str, list[Mapping[str, object]]],
) -> nodes.bullet_list | None:
    """Link runtime-aware narratives without copying their assurance claims."""
    result = nodes.bullet_list()
    added = False
    for kind in _VERIFICATION_KINDS:
        for item in grouped.get(kind, []):
            target = _runtime_url(context, item)
            if target is None:
                continue
            entry = nodes.list_item()
            paragraph = nodes.paragraph()
            paragraph += nodes.reference(
                "",
                human_test_title(item.get("title")),
                refuri=target,
            )
            paragraph += nodes.Text(
                " — inspect execution path, envelope, captured boundary interactions, "
                "proof basis, and explicit limits."
            )
            entry += paragraph
            result += entry
            added = True
    return result if added else None


def _runtime_assurance_layer(
    context: AssuranceRenderContext,
    grouped: Mapping[str, list[Mapping[str, object]]],
) -> nodes.list_item:
    """Render runtime-assurance drill-down as links to retained narratives."""
    links = _assurance_links(context, grouped)
    if links is None:
        return _layer_item(
            "Runtime assurance",
            nodes.paragraph(
                text=(
                    "No runtime-assurance narrative is available for current proof. "
                    "The graph relation remains visible above."
                )
            ),
        )
    return _layer_item(
        "Runtime assurance",
        [
            nodes.paragraph(
                text=(
                    "Retained runtime and coverage facts stay authoritative in the "
                    "concrete verification narratives:"
                )
            ),
            links,
        ],
    )


def _gap_list(health: SpecificationHealth) -> nodes.bullet_list | None:
    """Render only actionable current proof gaps."""
    gaps: list[str] = []
    if health.missing_evidence:
        gaps.append(f"Missing evidence: {', '.join(health.missing_evidence)}")
    if health.blocked_by:
        blocked = ", ".join(health.blocked_by)
        gaps.append(f"Blocked by incomplete child contracts: {blocked}")
    if health.gap_reason:
        gaps.append(health.gap_reason)
    if not gaps:
        return None
    result = nodes.bullet_list()
    for gap in gaps:
        item = nodes.list_item()
        item += nodes.paragraph(text=gap)
        result += item
    return result


def contract_section(
    context: AssuranceRenderContext,
    contract: Mapping[str, object],
    health: SpecificationHealth,
    proof: list[Mapping[str, object]],
    counts: Mapping[str, EvidenceCounts],
) -> nodes.section:
    """Build one complete layered proof reading path."""
    contract_id = str(contract["id"])
    section = nodes.section(ids=[f"assurance-{contract_id.lower()}"])
    title = nodes.title()
    title += _reference(
        context,
        contract,
        label=f"{contract_id} — {contract.get('title') or contract_id}",
    )
    section += title

    state = nodes.paragraph()
    state += nodes.strong(text="Current proof: ")
    state += nodes.Text("Complete" if health.deep_covered else "Incomplete")
    section += state

    grouped = _proof_groups(proof)
    layers = nodes.enumerated_list()
    layers += _contract_layer(contract)
    layers += _implementation_layer(context, contract, grouped)
    layers += _verification_layer(context, contract, grouped, counts)
    layers += _runtime_assurance_layer(context, grouped)
    section += layers

    gaps = _gap_list(health)
    if gaps is not None:
        section += nodes.rubric(text="What needs attention")
        section += gaps
    return section
