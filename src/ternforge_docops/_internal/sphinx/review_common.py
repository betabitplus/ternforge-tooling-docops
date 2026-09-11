"""Shared helpers for human review projections over the Needs graph."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from ternforge_docops._internal.verification.narrative import (
    verification_anchor,
    verification_docname,
)

if TYPE_CHECKING:
    from sphinx.application import Sphinx

_FIELD_RE = re.compile(
    r"\*\*(Statement|Constraint|Rationale|Verification intent)\.\*\*\s*",
)
_FEATURE_SOURCE_MIN_PARTS = 3


def normalize_ids(value: object) -> tuple[str, ...]:
    """Normalize resolved Needs link values to target identifiers."""
    if isinstance(value, str):
        values = value.split(",")
    elif isinstance(value, list | tuple):
        values = value
    else:
        return ()
    result: list[str] = []
    for item in values:
        target = str(getattr(item, "id", item)).strip().split("[", 1)[0]
        if target:
            result.append(target)
    return tuple(result)


def need_sort_key(need: Mapping[str, object]) -> tuple[str, int, str]:
    """Keep authored document order where possible."""
    lineno = need.get("lineno")
    return (
        str(need.get("docname") or ""),
        int(lineno) if isinstance(lineno, int) else 0,
        str(need.get("title") or need.get("id") or ""),
    )


def need_url(app: Sphinx, fromdocname: str, need: Mapping[str, object]) -> str:
    """Return a relative canonical URL for one Need."""
    need_id = str(need["id"])
    target_doc = str(need.get("docname") or fromdocname)
    uri = app.builder.get_relative_uri(fromdocname, target_doc)
    return f"{uri}#{need_id}"


def review_slug(value: str) -> str:
    """Match the stable Living Specifications slug convention."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug or "behavior"


def bdd_docname(item: Mapping[str, object]) -> str | None:
    """Resolve one BDD testcase to its generated Living Specifications page."""
    source = str(item.get("gherkin_feature") or "").strip()
    if not source:
        return None
    path = PurePosixPath(source)
    if len(path.parts) < _FEATURE_SOURCE_MIN_PARTS or path.parts[0] != "features":
        return None
    return (
        "specifications/_generated/"
        f"{review_slug(path.parts[1])}/{review_slug(path.stem)}"
    )


def bdd_scenario_url(
    app: Sphinx,
    fromdocname: str,
    item: Mapping[str, object],
) -> str | None:
    """Link BDD evidence to the human scenario document instead of raw JUnit needs."""
    docname = bdd_docname(item)
    scenario = str(item.get("gherkin_scenario") or "").strip()
    if docname is None or not scenario:
        return None

    suffix = f"-{review_slug(scenario)}"
    anonlabels = app.env.domaindata.get("std", {}).get("anonlabels", {})
    matches = [
        target
        for label, target in anonlabels.items()
        if label.startswith("living-scenario-")
        and label.endswith(suffix)
        and target[0] == docname
    ]
    uri = app.builder.get_relative_uri(fromdocname, docname)
    if len(matches) == 1:
        return f"{uri}#{matches[0][1]}"
    return uri


def verification_narrative_url(
    app: Sphinx,
    fromdocname: str,
    item: Mapping[str, object],
) -> str | None:
    """Link non-BDD testcase evidence to its human verification narrative."""
    kind = str(item.get("verification_kind") or "").strip()
    classname = str(item.get("classname") or "").strip()
    name = str(
        item.get("case") or item.get("case_name") or item.get("title") or ""
    ).strip()
    if kind not in {"unit", "property", "integration", "e2e"}:
        return None
    if not classname or not name:
        return None
    docname = verification_docname(kind, classname)
    anchor = verification_anchor(kind, classname, name)
    uri = app.builder.get_relative_uri(fromdocname, docname)
    return f"{uri}#{anchor}"


def strip_inline_markup(value: str) -> str:
    """Keep reader prose plain and compact instead of exposing source markup."""
    return value.replace("**", "").replace(chr(96), "").replace("\n", " ").strip()


def content_fields(content: object) -> dict[str, str]:
    """Split the small authored requirement schema into human-facing fields."""
    text = str(content or "").strip()
    if not text:
        return {}
    matches = list(_FIELD_RE.finditer(text))
    if not matches:
        return {"Summary": strip_inline_markup(text)}

    fields: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        fields[match.group(1)] = strip_inline_markup(text[start:end])
    return fields


def human_test_title(title: object) -> str:
    """Turn pytest collection names into readable verification labels."""
    raw = str(title or "").strip()
    if not raw:
        return "Executed verification"
    parameter = ""
    if "[" in raw and raw.endswith("]"):
        raw, parameter = raw.rsplit("[", 1)
        parameter = parameter[:-1]
    raw = raw.removeprefix("test_")
    words = raw.replace("_", " ").strip()
    label = words[:1].upper() + words[1:] if words else "Executed verification"
    return f"{label} — {parameter}" if parameter else label


def current_revision(
    needs: Mapping[str, Mapping[str, object]],
    target_id: str,
    revision: int,
) -> bool:
    """Return whether a revision-pinned edge targets the current contract."""
    target = needs.get(target_id)
    return target is not None and target.get("revision") == revision
