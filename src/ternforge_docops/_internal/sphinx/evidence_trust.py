"""Evidence-of-evidence projection over producer trust and calibration records."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from docutils import nodes
from sphinx.util.docutils import SphinxDirective
from sphinx_needs.api import get_needs_view

from ternforge_docops._internal.sphinx.review_common import (
    need_sort_key,
    need_url,
    normalize_ids,
)

if TYPE_CHECKING:
    from sphinx.application import Sphinx


class _EvidenceTrustNode(nodes.General, nodes.Element):
    """Placeholder resolved after producer and qualification Needs are available."""


class EvidenceTrustDirective(SphinxDirective):
    """Render all evidence producers and the basis for trusting them."""

    has_content = False

    def run(self) -> list[nodes.Node]:
        """Insert one late-bound evidence-trust placeholder."""
        return [_EvidenceTrustNode()]


def producer_trust_anchor(producer_id: str) -> str:
    """Return the stable evidence-trust anchor for one producer."""
    return f"evidence-trust-{producer_id.casefold().replace('_', '-')}"


def producer_trust_url(app: Sphinx, fromdocname: str, producer_id: str) -> str:
    """Return a link to one producer on the shared evidence-trust page."""
    uri = app.builder.get_relative_uri(fromdocname, "evidence-trust")
    return f"{uri}#{producer_trust_anchor(producer_id)}"


def _reference(
    app: Sphinx,
    fromdocname: str,
    need: Mapping[str, object],
) -> nodes.reference:
    """Build one canonical Need reference."""
    label = str(need.get("title") or need.get("id") or "Evidence")
    return nodes.reference("", label, refuri=need_url(app, fromdocname, need))


def _external_reference(label: str, url: object) -> nodes.reference | nodes.Text:
    """Build one external evidence link only when a URL is retained."""
    value = str(url or "").strip()
    if not value:
        return nodes.Text(label)
    return nodes.reference("", label, refuri=value)


def _linked_records(
    needs: Mapping[str, Mapping[str, object]],
    producer: Mapping[str, object],
    relation: str,
) -> list[Mapping[str, object]]:
    """Resolve one producer relation through the authoritative graph."""
    return [
        needs[target_id]
        for target_id in normalize_ids(producer.get(relation))
        if target_id in needs
    ]


def _calibration_records(
    needs: Mapping[str, Mapping[str, object]],
    producer: Mapping[str, object],
) -> list[Mapping[str, object]]:
    """Merge producer-owned calibration with evidence-owned calibration backlinks."""
    record_ids = tuple(
        dict.fromkeys(
            (
                *normalize_ids(producer.get("calibrated_by")),
                *normalize_ids(producer.get("calibrates_back")),
            )
        )
    )
    return [needs[record_id] for record_id in record_ids if record_id in needs]


def _metadata(producer: Mapping[str, object]) -> nodes.bullet_list:
    """Render the purpose/risk/impact/residual-doubt producer contract."""
    values = (
        ("Role", producer.get("producer_role")),
        ("Version basis", producer.get("producer_version")),
        ("Impact if wrong", producer.get("producer_impact")),
        ("Purpose", producer.get("producer_purpose")),
        ("Risk if wrong", producer.get("risk_if_wrong")),
        ("Residual doubt", producer.get("residual_doubt")),
    )
    result = nodes.bullet_list()
    for label, value in values:
        item = nodes.list_item()
        paragraph = nodes.paragraph()
        paragraph += nodes.strong(text=f"{label}: ")
        paragraph += nodes.Text(str(value or "not declared"))
        item += paragraph
        result += item
    return result


def _qualification_detail(record: Mapping[str, object]) -> tuple[str, object]:
    """Return qualification metadata plus retained evidence URL."""
    values = (
        str(record.get("qualification_kind") or ""),
        str(record.get("target_version") or ""),
    )
    return " · ".join(value for value in values if value), record.get("evidence_url")


def _manual_detail(record: Mapping[str, object]) -> tuple[str, object]:
    """Return manual-verification metadata plus retained artifact URL."""
    values = (
        str(record.get("manual_date") or ""),
        str(record.get("target_version") or ""),
        str(record.get("manual_scope") or ""),
    )
    return " · ".join(value for value in values if value), record.get("artifact_url")


def _record_detail(record: Mapping[str, object]) -> tuple[str, object]:
    """Return compact metadata plus retained evidence URL for one trust record."""
    handlers = {
        "qualification": _qualification_detail,
        "manual": _manual_detail,
    }
    handler = handlers.get(str(record.get("type") or ""))
    if handler is not None:
        return handler(record)
    return str(record.get("experiment_date") or ""), record.get("source_url")


def _record_item(
    app: Sphinx,
    fromdocname: str,
    record: Mapping[str, object],
) -> nodes.list_item:
    """Render one qualification/calibration record."""
    item = nodes.list_item()
    paragraph = nodes.paragraph()
    paragraph += _reference(app, fromdocname, record)
    detail, evidence_url = _record_detail(record)
    if detail:
        paragraph += nodes.Text(f" — {detail}")
    if str(evidence_url or "").strip():
        paragraph += nodes.Text(" · ")
        paragraph += _external_reference("retained evidence", evidence_url)
    item += paragraph
    return item


def _record_list(
    app: Sphinx,
    fromdocname: str,
    records: list[Mapping[str, object]],
) -> nodes.bullet_list:
    """Render qualification/calibration records with retained source artifacts."""
    result = nodes.bullet_list()
    for record in records:
        result += _record_item(app, fromdocname, record)
    return result


def _producer_section(
    app: Sphinx,
    fromdocname: str,
    needs: Mapping[str, Mapping[str, object]],
    producer: Mapping[str, object],
) -> nodes.section:
    """Render one producer → trust basis → calibration assurance chain."""
    producer_id = str(producer["id"])
    section = nodes.section(ids=[producer_trust_anchor(producer_id)])
    title = nodes.title()
    title += _reference(app, fromdocname, producer)
    section += title
    section += _metadata(producer)

    trust = _linked_records(needs, producer, "qualified_by")
    section += nodes.rubric(text="Trust basis")
    section += (
        _record_list(app, fromdocname, trust)
        if trust
        else nodes.paragraph(text="No trust-basis evidence linked.")
    )

    calibration = _calibration_records(needs, producer)
    section += nodes.rubric(text="Calibration / independent verification")
    if calibration:
        status = nodes.paragraph()
        status += nodes.strong(text="Substitute fidelity: ")
        status += nodes.Text("calibration evidence linked.")
        section += status
        section += _record_list(app, fromdocname, calibration)
    elif str(producer.get("producer_role") or "") == "test-substitute":
        status = nodes.paragraph()
        status += nodes.strong(text="Substitute fidelity: ")
        status += nodes.Text("not calibrated against live external reality.")
        section += status
    else:
        section += nodes.paragraph(
            text="No separate calibration is declared for this producer role."
        )
    return section


def evidence_trust_nodes(
    app: Sphinx,
    fromdocname: str,
    needs: Mapping[str, Mapping[str, object]],
) -> list[nodes.Node]:
    """Render every declared evidence producer and its supporting evidence."""
    producers = sorted(
        (need for need in needs.values() if str(need.get("type") or "") == "producer"),
        key=need_sort_key,
    )
    if not producers:
        return [nodes.paragraph(text="No evidence producers are declared.")]
    return [
        _producer_section(app, fromdocname, needs, producer) for producer in producers
    ]


def replace_evidence_trust_nodes(
    app: Sphinx,
    doctree: nodes.document,
    fromdocname: str,
) -> None:
    """Resolve evidence-trust placeholders from the complete Needs graph."""
    needs = {
        str(need["id"]): need for need in get_needs_view(app).values() if need.get("id")
    }
    for node in list(doctree.findall(_EvidenceTrustNode)):
        node.replace_self(evidence_trust_nodes(app, fromdocname, needs))


def register_evidence_trust_view(app: Sphinx) -> None:
    """Register the producer trust/calibration evidence-of-evidence view."""
    app.add_node(_EvidenceTrustNode)
    app.add_directive("ternforge-evidence-trust", EvidenceTrustDirective)
    app.connect("doctree-resolved", replace_evidence_trust_nodes)
