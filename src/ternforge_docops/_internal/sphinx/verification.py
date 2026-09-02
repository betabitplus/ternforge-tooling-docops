"""Theme-native verification views built from the authoritative Needs graph."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from typing import TYPE_CHECKING

from docutils import nodes
from sphinx.util.docutils import SphinxDirective
from sphinx_needs.api import get_needs_view

if TYPE_CHECKING:
    from sphinx.application import Sphinx

_VERIFICATION_KINDS = ("bdd", "unit", "integration", "property", "e2e")


class _VerificationMatrixNode(nodes.General, nodes.Element):
    """Placeholder replaced after the complete Needs graph is available."""


class _VerificationMatrixDirective(SphinxDirective):
    """Render requirement-by-verification coverage from imported testcase Needs."""

    has_content = False

    def run(self) -> list[nodes.Node]:
        """Insert a placeholder resolved after the complete Needs graph exists."""
        return [_VerificationMatrixNode()]


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


def _verification_counts(app: Sphinx) -> dict[str, dict[str, tuple[int, int]]]:
    """Count total and passed testcase evidence by requirement and verification kind."""
    totals: dict[str, dict[str, list[int]]] = defaultdict(
        lambda: defaultdict(lambda: [0, 0])
    )
    for need in get_needs_view(app).filter_types(["testcase"]).values():
        kind = str(need.get("verification_kind") or "")
        if kind not in _VERIFICATION_KINDS:
            continue
        passed = str(need.get("result") or "") == "passed"
        for requirement_id in _verification_ids(need.get("verifies")):
            totals[requirement_id][kind][0] += 1
            if passed:
                totals[requirement_id][kind][1] += 1
    return {
        requirement_id: {
            kind: (counts[0], counts[1]) for kind, counts in by_kind.items()
        }
        for requirement_id, by_kind in totals.items()
    }


def _status_text(counts: tuple[int, int] | None, *, required: bool) -> str:
    """Render evidence counts with required/optional verification semantics."""
    if counts is None:
        return "MISSING" if required else "—"
    total, passed = counts
    if passed == total:
        return f"✓ {passed}/{total}" if required else f"+ {passed}/{total}"
    return f"✗ {passed}/{total}"


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
    counts: dict[str, dict[str, tuple[int, int]]],
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
                    "Product requirements",
                    _matrix_table(app, fromdocname, requirements, counts),
                )
            )
        if constraints:
            replacement.extend(
                _section(
                    "Engineering constraints",
                    _matrix_table(app, fromdocname, constraints, counts),
                )
            )
        if not replacement:
            replacement.append(nodes.paragraph(text="No requirements found."))
        node.replace_self(replacement)


def register_verification_view(app: Sphinx) -> None:
    """Register the DocOps verification matrix directive."""
    app.add_node(_VerificationMatrixNode)
    app.add_directive("ternforge-verification-matrix", _VerificationMatrixDirective)
    app.connect("doctree-resolved", _replace_matrix_nodes)
