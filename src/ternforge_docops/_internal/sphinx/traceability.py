"""Small traceability primitives over the authoritative Sphinx-Needs graph."""

from __future__ import annotations

import re
from collections.abc import Mapping

_REQUIREMENT_ID = re.compile(r"^(?:REQ|TREQ)_[A-Z0-9_]+$")
_REVISION_PIN = re.compile(
    r"^(?P<id>(?:REQ|TREQ)_[A-Z0-9_]+)\[revision==(?P<revision>[1-9][0-9]*)\]$"
)
_REVISION_CONDITION = re.compile(r"^revision==(?P<revision>[1-9][0-9]*)$")


def _structured_targets(links: object) -> tuple[tuple[str, int], ...]:
    """Read exact revision pins from Sphinx-Needs structured NeedLink objects."""
    targets: list[tuple[str, int]] = []
    for link in links if isinstance(links, list | tuple) else ():
        requirement_id = str(getattr(link, "id", ""))
        condition = getattr(link, "condition", None)
        if not _REQUIREMENT_ID.fullmatch(requirement_id) or not isinstance(
            condition, str
        ):
            continue
        match = _REVISION_CONDITION.fullmatch(condition)
        if match is not None:
            targets.append((requirement_id, int(match.group("revision"))))
    return tuple(targets)


def _serialized_targets(value: object) -> tuple[tuple[str, int], ...]:
    """Read exact revision pins from serialized Needs representations."""
    if isinstance(value, str):
        values = value.split(",")
    elif isinstance(value, list | tuple):
        values = value
    else:
        return ()
    targets: list[tuple[str, int]] = []
    for item in values:
        match = _REVISION_PIN.fullmatch(str(item).strip())
        if match is not None:
            targets.append((match.group("id"), int(match.group("revision"))))
    return tuple(targets)


def revision_pinned_targets(
    need: Mapping[str, object],
    link_type: str,
) -> tuple[tuple[str, int], ...]:
    """Return exact Ternforge requirement revision pins from one Needs link field."""
    get_links = getattr(need, "get_links", None)
    if callable(get_links):
        try:
            return _structured_targets(get_links(link_type, as_str=False))
        except (KeyError, TypeError):
            return ()
    return _serialized_targets(need.get(link_type))
