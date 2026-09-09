"""Py-testkit execution-enrichment parsing for Living Specifications."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ternforge_docops._internal.living_specs.models import (
    LivingContract,
    LivingImplementation,
)

BDD_IMPLEMENTATION_TYPE = "application/vnd.ternforge.bdd-implementation+json"
CONTRACT_TYPE = "application/vnd.ternforge.contract+json"
INTERNAL_ATTACHMENT_TYPES = frozenset({BDD_IMPLEMENTATION_TYPE, CONTRACT_TYPE})


def _safe_source_name(value: dict[str, Any]) -> str:
    """Return one attachment source only when it is a plain local filename."""
    source_name = str(value.get("source") or "")
    return source_name if source_name and Path(source_name).name == source_name else ""


def _source_name(value: dict[str, Any], media_type: str) -> str:
    """Return the first safe attachment filename for one internal media type."""
    values = value.get("attachments")
    if not isinstance(values, list):
        return ""
    match = next(
        (
            attachment
            for attachment in values
            if isinstance(attachment, dict)
            and str(attachment.get("type") or "") == media_type
        ),
        None,
    )
    return _safe_source_name(match) if match is not None else ""


def _payload(raw_results: Path, source_name: str) -> dict[str, Any]:
    """Read one valid versioned internal evidence payload or return an empty mapping."""
    if not source_name:
        return {}
    source = raw_results / source_name
    if not source.is_file():
        return {}
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        return {}
    return payload


def _implementation_lines(payload: dict[str, Any]) -> tuple[int, int] | None:
    """Return a valid captured implementation line range."""
    start_line = payload.get("start_line")
    end_line = payload.get("end_line")
    if not isinstance(start_line, int) or not isinstance(end_line, int):
        return None
    if start_line < 1 or end_line < start_line:
        return None
    return start_line, end_line


def _implementation_model(payload: dict[str, Any]) -> LivingImplementation | None:
    """Validate one implementation payload into the Living Specifications model."""
    path = str(payload.get("path") or "").strip()
    code = str(payload.get("source") or "").rstrip()
    if not path or not code:
        return None
    line_range = _implementation_lines(payload)
    if line_range is None:
        return None
    start_line, end_line = line_range
    return LivingImplementation(
        keyword=str(payload.get("keyword") or "").strip(),
        text=str(payload.get("text") or "").strip(),
        function=str(payload.get("function") or "").strip(),
        path=Path(path).as_posix(),
        start_line=start_line,
        end_line=end_line,
        source=code,
    )


def implementation(
    raw_results: Path, value: dict[str, Any]
) -> LivingImplementation | None:
    """Parse the exact BDD binding source emitted by py-testkit when available."""
    source_name = _source_name(value, BDD_IMPLEMENTATION_TYPE)
    return _implementation_model(_payload(raw_results, source_name))


def _contract_source_names(value: dict[str, Any]) -> tuple[str, ...]:
    """Return safe source filenames for live-contract attachments."""
    values = value.get("attachments")
    if not isinstance(values, list):
        return ()
    names: list[str] = []
    for attachment in values:
        if not isinstance(attachment, dict):
            continue
        if str(attachment.get("type") or "") != CONTRACT_TYPE:
            continue
        if source_name := _safe_source_name(attachment):
            names.append(source_name)
    return tuple(names)


def _contract_content(payload: dict[str, Any]) -> tuple[str, str, object | None] | None:
    """Return validated contract kind, signature, and optional schema payload."""
    kind = str(payload.get("kind") or "").strip()
    if kind == "schema":
        schema = payload.get("schema")
        return (kind, "", schema) if isinstance(schema, dict) else None
    if kind == "callable":
        signature = str(payload.get("signature") or "").strip()
        return (kind, signature, None) if signature else None
    return None


def _contract_model(payload: dict[str, Any]) -> LivingContract | None:
    """Validate one live contract payload into the presentation model."""
    name = str(payload.get("name") or "").strip()
    if not name:
        return None
    content = _contract_content(payload)
    if content is None:
        return None
    kind, signature, schema = content
    return LivingContract(
        name=name,
        kind=kind,
        qualified_name=str(payload.get("qualified_name") or "").strip(),
        description=str(payload.get("description") or "").strip(),
        signature=signature,
        schema=schema,
    )


def contracts(raw_results: Path, value: dict[str, Any]) -> tuple[LivingContract, ...]:
    """Return all valid live contracts captured inside one executed BDD step."""
    return tuple(
        contract
        for source_name in _contract_source_names(value)
        if (contract := _contract_model(_payload(raw_results, source_name))) is not None
    )
