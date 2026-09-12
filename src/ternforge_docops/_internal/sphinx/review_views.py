"""Human review projections over the authoritative Sphinx-Needs graph."""

from __future__ import annotations

from typing import TYPE_CHECKING

from docutils import nodes
from sphinx.util.docutils import SphinxDirective
from sphinx_needs.api import get_needs_view

from ternforge_docops._internal.sphinx.specification_map import specification_map_html
from ternforge_docops._internal.sphinx.traceability_reader import reader_html

if TYPE_CHECKING:
    from sphinx.application import Sphinx


class _TraceabilityReaderNode(nodes.General, nodes.Element):
    """Placeholder for the document-like traceability reader."""


class _SpecificationMapNode(nodes.General, nodes.Element):
    """Placeholder for the compact specification health map."""


class _TraceabilityReaderDirective(SphinxDirective):
    """Render the specification as a normal, vertically readable document."""

    has_content = False

    def run(self) -> list[nodes.Node]:
        """Insert one late-bound reader placeholder."""
        return [_TraceabilityReaderNode()]


class _SpecificationMapDirective(SphinxDirective):
    """Render the complete specification hierarchy as a compact health treemap."""

    has_content = False

    def run(self) -> list[nodes.Node]:
        """Insert one late-bound health-map placeholder."""
        return [_SpecificationMapNode()]


def _replace_review_nodes(
    app: Sphinx,
    doctree: nodes.document,
    fromdocname: str,
) -> None:
    """Resolve review placeholders after the complete Needs graph exists."""
    view = get_needs_view(app)
    needs = {str(need["id"]): need for need in view.values() if need.get("id")}

    for node in list(doctree.findall(_TraceabilityReaderNode)):
        if app.builder.format == "html":
            replacement: nodes.Node = nodes.raw(
                "",
                reader_html(app, fromdocname, needs),
                format="html",
            )
        else:
            replacement = nodes.paragraph(
                text=(
                    "The document-like traceability reader is available "
                    "in the HTML portal."
                )
            )
        node.replace_self(replacement)

    for node in list(doctree.findall(_SpecificationMapNode)):
        if app.builder.format == "html":
            replacement = nodes.raw(
                "",
                specification_map_html(app, fromdocname, needs),
                format="html",
            )
        else:
            replacement = nodes.paragraph(
                text=(
                    "The interactive specification health map is available "
                    "in the HTML portal."
                )
            )
        node.replace_self(replacement)


def register_review_views(app: Sphinx) -> None:
    """Register human review projections over the authoritative graph."""
    app.add_node(_TraceabilityReaderNode)
    app.add_node(_SpecificationMapNode)
    app.add_directive("ternforge-traceability-reader", _TraceabilityReaderDirective)
    app.add_directive("ternforge-specification-map", _SpecificationMapDirective)
    app.connect("doctree-resolved", _replace_review_nodes)
