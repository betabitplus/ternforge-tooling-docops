"""Regression coverage for the Ternforge SimplePDF compatibility adapter."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from bs4 import BeautifulSoup

from ternforge_docops._internal.documentation.simplepdf import (
    configure_simplepdf_anchors,
    normalize_singlehtml_anchors,
)

if TYPE_CHECKING:
    from sphinx.application import Sphinx


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(normalize_singlehtml_anchors(html), "html.parser")


def test_singlehtml_anchors_are_scoped_by_document_order() -> None:
    """Duplicate section ids become document-scoped and links follow them."""
    soup = _soup(
        """
        <span id="document-alpha"></span>
        <section id="shared"><a href="#shared">alpha local</a></section>
        <a href="#document-beta#shared">alpha to beta</a>
        <span id="document-beta"></span>
        <section id="shared"><a href="#shared">beta local</a></section>
        """
    )

    assert soup.find(id="document-alpha--shared") is not None
    assert soup.find(id="document-beta--shared") is not None
    assert soup.find("a", string="alpha local")["href"] == "#document-alpha--shared"
    assert soup.find("a", string="alpha to beta")["href"] == "#document-beta--shared"
    assert soup.find("a", string="beta local")["href"] == "#document-beta--shared"


def test_unresolvable_internal_targets_become_plain_links() -> None:
    """Dangling PDF-internal targets do not reach WeasyPrint."""
    soup = _soup(
        """
        <span id="document-alpha"></span>
        <a href="#missing">missing local</a>
        <a href="#document-missing#section">missing document</a>
        <a href="https://example.com/">external</a>
        """
    )

    assert "href" not in soup.find("a", string="missing local").attrs
    assert "href" not in soup.find("a", string="missing document").attrs
    assert soup.find("a", string="external")["href"] == "https://example.com/"


def test_normalized_internal_links_resolve_to_unique_ids() -> None:
    """The normalized PDF DOM contains no duplicate or malformed internal anchors."""
    soup = _soup(
        """
        <span id="document-alpha"></span>
        <h2 id="idea-branch">Alpha</h2>
        <a href="#idea-branch">alpha local</a>
        <a href="#document-beta#idea-branch">alpha to beta</a>
        <span id="document-beta"></span>
        <h2 id="idea-branch">Beta</h2>
        <a href="#document-alpha#idea-branch">beta to alpha</a>
        """
    )

    ids = [element["id"] for element in soup.find_all(id=True)]
    assert all(count == 1 for count in Counter(ids).values())

    final_ids = set(ids)
    internal_hrefs = [
        link["href"]
        for link in soup.find_all("a", href=True)
        if link["href"].startswith("#")
    ]
    assert all(href.count("#") == 1 for href in internal_hrefs)
    assert all(href[1:] in final_ids for href in internal_hrefs)


def test_simplepdf_builder_hook_normalizes_after_upstream_repair(
    tmp_path: Path,
) -> None:
    """The builder hook keeps upstream repair and then normalizes its HTML."""

    class FakeSimplePdfBuilder:
        name = "simplepdf"

        def __init__(self) -> None:
            self.calls = 0

        def _toctree_fix(self, html: str) -> str:
            self.calls += 1
            return html

    builder = FakeSimplePdfBuilder()
    app = cast("Sphinx", SimpleNamespace(builder=builder, outdir=str(tmp_path)))

    configure_simplepdf_anchors(app)
    normalized = builder._toctree_fix(
        """
        <span id="document-alpha"></span>
        <h2 id="shared">Alpha</h2>
        <a href="#document-alpha#shared">target</a>
        """
    )
    soup = BeautifulSoup(normalized, "html.parser")

    assert builder.calls == 1
    assert soup.find(id="document-alpha--shared") is not None
    assert soup.find("a", string="target")["href"] == "#document-alpha--shared"


def test_simplepdf_builder_hook_removes_generic_monospace_font_faces(
    tmp_path: Path,
) -> None:
    """Known crashing upstream generic font-face rules are removed only for PDF."""

    class FakeSimplePdfBuilder:
        name = "simplepdf"

        @staticmethod
        def _toctree_fix(html: str) -> str:
            return html

    static = tmp_path / "_static"
    static.mkdir()
    css_path = static / "main.css"
    css_path.write_text(
        """
        @font-face {
          font-family: monospace;
          src: url(fonts/FiraMono-Regular.ttf);
        }
        @font-face {
          font-family: CustomMono;
          src: url(fonts/CustomMono-Regular.ttf);
        }
        pre { font-family: monospace; }
        """,
        encoding="utf-8",
    )
    app = cast(
        "Sphinx",
        SimpleNamespace(builder=FakeSimplePdfBuilder(), outdir=str(tmp_path)),
    )

    configure_simplepdf_anchors(app)
    patched = css_path.read_text(encoding="utf-8")

    assert "FiraMono-Regular.ttf" not in patched
    assert "CustomMono-Regular.ttf" in patched
    assert "pre { font-family: monospace; }" in patched
