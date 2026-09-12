"""Compatibility helpers for reliable Sphinx-SimplePDF single-HTML anchors."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol, cast

from bs4 import BeautifulSoup
from bs4.element import Tag

if TYPE_CHECKING:
    from sphinx.application import Sphinx


class _SimplePdfBuilder(Protocol):
    """Structural type for the upstream builder hook used by the adapter."""

    name: str
    _toctree_fix: Callable[[str], str]


def _unique_scoped_id(document_id: str, fragment: str, used_ids: set[str]) -> str:
    """Return a deterministic document-scoped HTML id."""
    base = f"{document_id}--{fragment}"
    candidate = base
    suffix = 2
    while candidate in used_ids:
        candidate = f"{base}--{suffix}"
        suffix += 1
    return candidate


def _scope_document_ids(
    soup: BeautifulSoup,
) -> tuple[dict[int, str | None], dict[tuple[str, str], str], set[str]]:
    """Scope single-HTML ids according to preceding ``document-*`` markers."""
    used_ids: set[str] = set()
    scopes: dict[int, str | None] = {}
    scoped_ids: dict[tuple[str, str], str] = {}
    current_document: str | None = None

    for element in soup.find_all(name=True):
        value = element.get("id")
        if isinstance(value, str) and value.startswith("document-"):
            current_document = value
            scopes[id(element)] = current_document
            used_ids.add(value)
            continue

        scopes[id(element)] = current_document
        if not isinstance(value, str):
            continue
        if current_document is None:
            used_ids.add(value)
            continue

        scoped = _unique_scoped_id(current_document, value, used_ids)
        element["id"] = scoped
        used_ids.add(scoped)
        scoped_ids.setdefault((current_document, value), scoped)

    final_ids = {
        value
        for element in soup.find_all(id=True)
        if isinstance((value := element.get("id")), str)
    }
    return scopes, scoped_ids, final_ids


def _rewrite_internal_link(
    link: Tag,
    *,
    scope: str | None,
    scoped_ids: dict[tuple[str, str], str],
    final_ids: set[str],
) -> None:
    """Rewrite one internal link to a valid single-fragment PDF target."""
    href = link.get("href")
    if not isinstance(href, str) or not href.startswith("#"):
        return

    target = href[1:]
    if "#" in target:
        document_id, fragment = target.split("#", 1)
        scoped = scoped_ids.get((document_id, fragment))
        if scoped is not None:
            link["href"] = f"#{scoped}"
        elif not fragment and document_id in final_ids:
            link["href"] = f"#{document_id}"
        else:
            del link["href"]
        return

    scoped = scoped_ids.get((scope, target)) if scope is not None else None
    if scoped is not None:
        link["href"] = f"#{scoped}"
    elif target not in final_ids:
        del link["href"]


def normalize_singlehtml_anchors(html: str) -> str:
    """Make Sphinx single-HTML internal anchors valid for WeasyPrint.

    Sphinx-SimplePDF can leave cross-document links such as
    ``#document-path#section`` while the section itself keeps an unscoped id.
    ``document-*`` markers are standalone spans in document order, not
    ancestors, so ids and links must be normalized using that ordering.
    """
    soup = BeautifulSoup(html, "html.parser")
    scopes, scoped_ids, final_ids = _scope_document_ids(soup)

    for link in soup.find_all("a", href=True):
        _rewrite_internal_link(
            link,
            scope=scopes.get(id(link)),
            scoped_ids=scoped_ids,
            final_ids=final_ids,
        )

    return str(soup)


def configure_simplepdf_anchors(app: Sphinx) -> None:
    """Wrap the upstream SimplePDF TOC repair without importing WeasyPrint here."""
    if getattr(app.builder, "name", None) != "simplepdf":
        return

    builder = cast("_SimplePdfBuilder", app.builder)
    original = builder._toctree_fix

    def normalize_after_upstream(html: str) -> str:
        """Preserve upstream TOC repair before applying anchor normalization."""
        return normalize_singlehtml_anchors(original(html))

    builder._toctree_fix = normalize_after_upstream
