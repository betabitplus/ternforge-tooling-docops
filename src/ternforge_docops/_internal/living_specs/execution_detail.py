"""Execution-enrichment RST for Living Specifications."""

from __future__ import annotations

import json
from urllib.parse import quote

from ternforge_docops._internal.living_specs.models import (
    LivingAttachment,
    LivingContract,
    LivingImplementation,
)
from ternforge_docops._internal.living_specs.rst import (
    append_rst,
    code_block,
    rst_inline,
)

_MAX_OUTCOME_FIELDS = 8
_MAX_OUTCOME_VALUE = 220


def _compact_json_value(value: object) -> str:
    """Render one nested observed value as compact deterministic JSON."""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        return str(value)


def _compact_mapping(value: dict[object, object]) -> str:
    """Render one mapping as readable key=value pairs without semantic inference."""
    parts = [
        f"{key}={_compact_json_value(item)}"
        for key, item in list(value.items())[:_MAX_OUTCOME_FIELDS]
    ]
    if len(value) > _MAX_OUTCOME_FIELDS:
        parts.append("…")
    return " · ".join(parts)


def _compact_outcome_value(value: object) -> str:
    """Render one observed value compactly without inventing semantic meaning."""
    if isinstance(value, dict):
        rendered = _compact_mapping(value)
    elif isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict):
        rendered = _compact_mapping(value[0])
    else:
        rendered = _compact_json_value(value)
    rendered = " ".join(rendered.split())
    if len(rendered) > _MAX_OUTCOME_VALUE:
        return f"{rendered[: _MAX_OUTCOME_VALUE - 1]}…"
    return rendered


def render_observed_outcome(
    lines: list[str], attachment: LivingAttachment, indent: int
) -> None:
    """Render a compact deterministic view of explicitly named Result evidence."""
    if attachment.name.casefold() != "result" or attachment.source is None:
        return
    try:
        payload = json.loads(attachment.source.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return

    append_rst(lines, indent, ".. card:: Observed outcome")
    append_rst(lines, 0)
    body = indent + 3
    if isinstance(payload, dict) and payload:
        items = list(payload.items())
        for key, value in items[:_MAX_OUTCOME_FIELDS]:
            append_rst(
                lines,
                body,
                f"* **{rst_inline(str(key))}:** "
                f"{rst_inline(_compact_outcome_value(value))}",
            )
        if len(items) > _MAX_OUTCOME_FIELDS:
            append_rst(lines, body, "* …")
    else:
        append_rst(lines, body, rst_inline(_compact_outcome_value(payload)))
    append_rst(lines, 0)


def implementation_url(
    implementation: LivingImplementation,
    repository_source_base: str,
) -> str:
    """Return a revision-pinned repository URL for one captured implementation."""
    if not repository_source_base:
        return ""
    path = quote(implementation.path, safe="/")
    return (
        f"{repository_source_base.rstrip('/')}/{path}"
        f"#L{implementation.start_line}-L{implementation.end_line}"
    )


def render_executable_usage(
    lines: list[str],
    implementation: LivingImplementation,
    indent: int,
    repository_source_base: str,
) -> None:
    """Render the exact executed When binding as a collapsed technical drill-down."""
    append_rst(lines, indent, ".. dropdown:: Executable usage")
    append_rst(lines, 0)
    body = indent + 3
    source_url = implementation_url(implementation, repository_source_base)
    if source_url:
        append_rst(
            lines,
            body,
            f":bdg-link-secondary-line:`Source ↗ <{source_url}>`",
        )
        append_rst(lines, 0)
    append_rst(
        lines,
        body,
        "This is the exact pytest-bdd binding executed for this step, not "
        "documentation-only pseudocode.",
    )
    append_rst(lines, 0)
    code_block(lines, body, "python", implementation.source)


def _render_contract(
    lines: list[str],
    contract: LivingContract,
    indent: int,
) -> None:
    """Render one contract derived from the live schema class or callable."""
    append_rst(lines, indent, f"**{rst_inline(contract.name)}**")
    append_rst(lines, 0)
    if contract.qualified_name:
        display_name = contract.qualified_name.rsplit(".", 1)[-1]
        append_rst(lines, indent, f"``{rst_inline(display_name)}``")
        append_rst(lines, 0)
    if contract.description:
        description = " ".join(contract.description.split())
        append_rst(lines, indent, rst_inline(description))
        append_rst(lines, 0)
    if contract.kind == "schema" and contract.schema is not None:
        code_block(
            lines,
            indent,
            "json",
            json.dumps(contract.schema, indent=2, ensure_ascii=False),
        )
    elif contract.kind == "callable" and contract.signature:
        callable_name = contract.qualified_name.rsplit(".", 1)[-1] or contract.name
        code_block(
            lines,
            indent,
            "python",
            f"{callable_name}{contract.signature}",
        )


def render_public_contract(
    lines: list[str],
    contracts: tuple[LivingContract, ...],
    indent: int,
) -> None:
    """Render live schemas/tools as a collapsed contract drill-down."""
    if not contracts:
        return
    append_rst(lines, indent, ".. dropdown:: Public contract")
    append_rst(lines, 0)
    body = indent + 3
    append_rst(
        lines,
        body,
        "Derived from the exact schema classes and callables used by this execution.",
    )
    append_rst(lines, 0)
    for contract in contracts:
        _render_contract(lines, contract, body)
