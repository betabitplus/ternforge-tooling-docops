"""Theme-native verification views built from the authoritative Needs graph."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from docutils import nodes
from sphinx.util.docutils import SphinxDirective
from sphinx_needs.api import get_needs_view

from ternforge_docops._internal.sphinx.revision_evidence import (
    VERIFICATION_KINDS as _VERIFICATION_KINDS,
    EvidenceCounts as _EvidenceCounts,
    verification_counts_from_needs as _verification_counts_from_needs,
)

if TYPE_CHECKING:
    from sphinx.application import Sphinx


class _VerificationMatrixNode(nodes.General, nodes.Element):
    """Placeholder replaced after the complete Needs graph is available."""


class _ContractProvenanceNode(nodes.General, nodes.Element):
    """Placeholder for graph-native provenance behind one verified contract."""


class _VerificationMatrixDirective(SphinxDirective):
    """Render requirement-by-verification coverage from imported testcase Needs."""

    has_content = False

    def run(self) -> list[nodes.Node]:
        """Insert a placeholder resolved after the complete Needs graph exists."""
        return [_VerificationMatrixNode()]


class _ContractProvenanceDirective(SphinxDirective):
    """Render graph-native provenance for one or more verified Need identifiers."""

    has_content = False
    required_arguments = 1
    final_argument_whitespace = True

    def run(self) -> list[nodes.Node]:
        """Insert a provenance placeholder resolved against the complete Needs graph."""
        requirements = tuple(
            value.strip() for value in self.arguments[0].split(",") if value.strip()
        )
        node = _ContractProvenanceNode()
        node["requirements"] = requirements
        return [node]


def _verification_ids(value: object) -> tuple[str, ...]:
    """Normalize testcase verifies values to unversioned Need identifiers."""
    if isinstance(value, str):
        values = value.split(",")
    elif isinstance(value, list | tuple):
        values = value
    else:
        return ()
    return tuple(
        str(item).strip().split("[", 1)[0] for item in values if str(item).strip()
    )


def _verification_counts(app: Sphinx) -> dict[str, dict[str, _EvidenceCounts]]:
    """Count revision-current verification evidence from the authoritative graph."""
    return _verification_counts_from_needs(list(get_needs_view(app).values()))


def _status_text(counts: _EvidenceCounts | None, *, required: bool) -> str:
    """Render current evidence plus any stale revision references."""
    if counts is None:
        return "MISSING" if required else "—"
    total, passed, outdated, predated = counts
    parts: list[str] = []
    if total:
        if passed == total:
            parts.append(f"✓ {passed}/{total}" if required else f"+ {passed}/{total}")
        else:
            parts.append(f"✗ {passed}/{total}")
    if outdated:
        parts.append(f"OUTDATED {outdated}")
    if predated:
        parts.append(f"PREDATED {predated}")
    if parts:
        return " · ".join(parts)
    return "MISSING" if required else "—"


def _entry(text: str, *, header: bool = False) -> nodes.entry:
    """Build one plain-text docutils table entry."""
    entry = nodes.entry()
    if header:
        entry["classes"].append("head")
    paragraph = nodes.paragraph()
    paragraph += nodes.Text(text)
    entry += paragraph
    return entry


def _requirement_entry(
    app: Sphinx,
    fromdocname: str,
    need: Mapping[str, object],
) -> nodes.entry:
    """Build a linked requirement cell with title and status context."""
    entry = nodes.entry()
    paragraph = nodes.paragraph()
    target_doc = str(need.get("docname") or fromdocname)
    uri = app.builder.get_relative_uri(fromdocname, target_doc)
    requirement_id = str(need["id"])
    reference = nodes.reference(
        "",
        requirement_id,
        refuri=f"{uri}#{requirement_id}",
    )
    paragraph += reference
    title = str(need.get("title") or "")
    status = str(need.get("status") or "")
    detail = " · ".join(value for value in (title, status) if value)
    if detail:
        paragraph += nodes.Text(f" — {detail}")
    entry += paragraph
    return entry


def _matrix_table(
    app: Sphinx,
    fromdocname: str,
    needs: list[Mapping[str, object]],
    counts: dict[str, dict[str, _EvidenceCounts]],
) -> nodes.table:
    """Build a theme-native verification matrix for one Need category."""
    table = nodes.table(classes=["docutils", "align-default"])
    tgroup = nodes.tgroup(cols=len(_VERIFICATION_KINDS) + 1)
    table += tgroup
    tgroup += nodes.colspec(colwidth=45)
    for _ in _VERIFICATION_KINDS:
        tgroup += nodes.colspec(colwidth=11)

    thead = nodes.thead()
    header = nodes.row()
    header += _entry("Requirement", header=True)
    for kind in _VERIFICATION_KINDS:
        header += _entry(kind.upper(), header=True)
    thead += header
    tgroup += thead

    tbody = nodes.tbody()
    for need in sorted(needs, key=lambda item: str(item["id"])):
        row = nodes.row()
        row += _requirement_entry(app, fromdocname, need)
        required_raw = need.get("required_evidence") or []
        required = (
            {str(value) for value in required_raw}
            if isinstance(required_raw, list | tuple | set | frozenset)
            else set()
        )
        requirement_id = str(need["id"])
        for kind in _VERIFICATION_KINDS:
            row += _entry(
                _status_text(
                    counts.get(requirement_id, {}).get(kind),
                    required=kind in required,
                )
            )
        tbody += row
    tgroup += tbody
    return table


def _section(title: str, table: nodes.table) -> list[nodes.Node]:
    """Wrap a verification matrix with its category heading."""
    return [nodes.rubric(text=title), table]


def _replace_matrix_nodes(
    app: Sphinx,
    doctree: nodes.document,
    fromdocname: str,
) -> None:
    """Resolve matrix placeholders after the complete Needs graph is available."""
    view = get_needs_view(app)
    counts = _verification_counts(app)
    requirements = list(view.filter_types(["req"]).values())
    constraints = list(view.filter_types(["treq"]).values())
    for node in list(doctree.findall(_VerificationMatrixNode)):
        replacement: list[nodes.Node] = []
        if requirements:
            replacement.extend(
                _section(
                    "Requirements",
                    _matrix_table(app, fromdocname, requirements, counts),
                )
            )
        if constraints:
            replacement.extend(
                _section(
                    "Technical requirements",
                    _matrix_table(app, fromdocname, constraints, counts),
                )
            )
        if not replacement:
            replacement.append(nodes.paragraph(text="No requirements found."))
        node.replace_self(replacement)


def _needs_by_id(app: Sphinx) -> dict[str, Mapping[str, object]]:
    """Index the authoritative Needs graph by stable identifier."""
    return {
        str(need["id"]): need for need in get_needs_view(app).values() if need.get("id")
    }


def _related_ids(
    needs: Mapping[str, Mapping[str, object]],
    source_ids: tuple[str, ...],
    relation: str,
    allowed_types: frozenset[str],
) -> tuple[str, ...]:
    """Follow one declared relation while preserving graph declaration order."""
    related: list[str] = []
    for source_id in source_ids:
        source = needs.get(source_id)
        if source is None:
            continue
        for target_id in _verification_ids(source.get(relation)):
            target = needs.get(target_id)
            if (
                target is not None
                and str(target.get("type") or "") in allowed_types
                and target_id not in related
            ):
                related.append(target_id)
    return tuple(related)


def _provenance_groups(
    needs: Mapping[str, Mapping[str, object]],
    requirement_ids: tuple[str, ...],
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Resolve contract → constraint/ADR/EXP/implementation provenance layers."""
    roots = tuple(
        requirement_id for requirement_id in requirement_ids if requirement_id in needs
    )
    constraints = _related_ids(
        needs,
        roots,
        "derives_back",
        frozenset({"treq"}),
    )
    contract_layer = tuple(dict.fromkeys((*roots, *constraints)))
    decisions = _related_ids(
        needs,
        contract_layer,
        "affects_back",
        frozenset({"adr"}),
    )
    research = _related_ids(
        needs,
        tuple(dict.fromkeys((*contract_layer, *decisions))),
        "informs_back",
        frozenset({"exp"}),
    )
    implementations = _related_ids(
        needs,
        contract_layer,
        "implements_back",
        frozenset({"impl"}),
    )
    return (
        ("Verified contract", roots),
        ("Technical requirements", constraints),
        ("Architecture decisions", decisions),
        ("Research evidence", research),
        ("Implementation loci", implementations),
    )


def _need_reference(
    app: Sphinx,
    fromdocname: str,
    need: Mapping[str, object],
) -> nodes.reference:
    """Build one theme-native internal link to an existing Need."""
    need_id = str(need["id"])
    target_doc = str(need.get("docname") or fromdocname)
    uri = app.builder.get_relative_uri(fromdocname, target_doc)
    title = str(need.get("title") or "")
    label = f"{need_id} · {title}" if title else need_id
    return nodes.reference("", label, refuri=f"{uri}#{need_id}")


def _provenance_list(
    app: Sphinx,
    fromdocname: str,
    needs: Mapping[str, Mapping[str, object]],
    groups: tuple[tuple[str, tuple[str, ...]], ...],
) -> nodes.bullet_list:
    """Render provenance layers as a stock docutils bullet list."""
    result = nodes.bullet_list()
    for label, need_ids in groups:
        if not need_ids:
            continue
        item = nodes.list_item()
        paragraph = nodes.paragraph()
        paragraph += nodes.strong(text=f"{label}: ")
        for index, need_id in enumerate(need_ids):
            if index:
                paragraph += nodes.Text(", ")
            paragraph += _need_reference(app, fromdocname, needs[need_id])
        item += paragraph
        result += item
    return result


def _replace_provenance_nodes(
    app: Sphinx,
    doctree: nodes.document,
    fromdocname: str,
) -> None:
    """Resolve contract provenance placeholders from the complete Needs graph."""
    needs = _needs_by_id(app)
    for node in list(doctree.findall(_ContractProvenanceNode)):
        requirement_ids = tuple(str(value) for value in node.get("requirements", ()))
        groups = _provenance_groups(needs, requirement_ids)
        node.replace_self(_provenance_list(app, fromdocname, needs, groups))


def register_verification_view(app: Sphinx) -> None:
    """Register theme-native verification and contract-provenance views."""
    app.add_node(_VerificationMatrixNode)
    app.add_node(_ContractProvenanceNode)
    app.add_directive("ternforge-verification-matrix", _VerificationMatrixDirective)
    app.add_directive("ternforge-contract-provenance", _ContractProvenanceDirective)
    app.connect("doctree-resolved", _replace_matrix_nodes)
    app.connect("doctree-resolved", _replace_provenance_nodes)
