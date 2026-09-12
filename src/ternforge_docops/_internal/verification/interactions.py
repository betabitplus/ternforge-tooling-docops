"""Typed normalization for captured verification boundary interactions."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class BoundaryInteractionObservation:
    """One explicitly captured participant interaction at a verification boundary."""

    boundary: str
    interaction: str
    participant: str
    target: str
    transport: str


@dataclass(frozen=True)
class ExternalSubstituteObservation:
    """Legacy normalized shape for one external boundary replacement."""

    producer: str
    boundary: str
    mode: str
    transport: str
    target: str


def _payload_text(payload: Mapping[str, object], key: str) -> str:
    """Return one normalized string field from an observation payload."""
    return str(payload.get(key) or "").strip()


def _typed_boundary_interaction(
    payload: Mapping[str, object],
) -> BoundaryInteractionObservation | None:
    """Normalize the first-class boundary-interaction payload."""
    boundary = _payload_text(payload, "boundary")
    interaction = _payload_text(payload, "interaction")
    participant = _payload_text(payload, "participant")
    target = _payload_text(payload, "target")
    if not all((boundary, interaction, participant, target)):
        return None
    return BoundaryInteractionObservation(
        boundary=boundary,
        interaction=interaction,
        participant=participant,
        target=target,
        transport=_payload_text(payload, "transport"),
    )


def _legacy_boundary_interaction(
    payload: Mapping[str, object],
) -> BoundaryInteractionObservation | None:
    """Project a legacy external-substitute payload into the interaction model."""
    producer = _payload_text(payload, "producer")
    if not producer:
        return None
    return BoundaryInteractionObservation(
        boundary=_payload_text(payload, "boundary") or "external",
        interaction="substitute",
        participant=producer,
        target=_payload_text(payload, "target") or "external system",
        transport=_payload_text(payload, "transport"),
    )


def normalize_boundary_interaction(
    kind: str,
    payload: Mapping[str, object],
) -> BoundaryInteractionObservation | None:
    """Normalize one captured observation into the interaction model."""
    normalizers = {
        "boundary-interaction": _typed_boundary_interaction,
        "external-substitute": _legacy_boundary_interaction,
    }
    normalizer = normalizers.get(kind)
    return normalizer(payload) if normalizer is not None else None


def normalize_external_substitute(
    kind: str,
    payload: Mapping[str, object],
) -> ExternalSubstituteObservation | None:
    """Normalize one retained legacy external-substitute observation."""
    if kind != "external-substitute":
        return None
    producer = _payload_text(payload, "producer")
    if not producer:
        return None
    return ExternalSubstituteObservation(
        producer=producer,
        boundary=_payload_text(payload, "boundary"),
        mode=_payload_text(payload, "mode"),
        transport=_payload_text(payload, "transport"),
        target=_payload_text(payload, "target"),
    )
