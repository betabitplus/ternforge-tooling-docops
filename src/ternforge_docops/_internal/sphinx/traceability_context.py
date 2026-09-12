"""Typed rendering context shared by traceability reader components."""

from __future__ import annotations

import html
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ternforge_docops._internal.sphinx.review_common import need_url

if TYPE_CHECKING:
    from sphinx.application import Sphinx


@dataclass(frozen=True)
class ReaderContext:
    """Shared data used while rendering one review document."""

    app: Sphinx
    fromdocname: str
    proof: Mapping[str, list[Mapping[str, object]]]
    reqs_by_feature: Mapping[str, list[Mapping[str, object]]]
    constraints_by_req: Mapping[str, list[Mapping[str, object]]]


def compact_need_link(
    context: ReaderContext,
    need: Mapping[str, object],
) -> str:
    """Render one human title without exposing the machine identifier."""
    url = html.escape(need_url(context.app, context.fromdocname, need))
    title = html.escape(str(need.get("title") or need["id"]))
    return f'<a href="{url}">{title}</a>'
