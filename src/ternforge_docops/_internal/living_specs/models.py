"""Data model for native Living Specifications presentation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LivingAttachment:
    """One retained attachment referenced by an Allure result or step."""

    name: str
    media_type: str
    source: Path | None
    output_name: str | None


@dataclass(frozen=True)
class LivingStep:
    """One executed Given/When/Then step with retained evidence."""

    name: str
    status: str
    attachments: tuple[LivingAttachment, ...]


@dataclass(frozen=True)
class LivingExample:
    """One current executed BDD example after history de-duplication."""

    name: str
    status: str
    epic: str
    feature: str
    feature_description: str
    rule: str
    story: str
    requirements: tuple[str, ...]
    tags: tuple[str, ...]
    steps: tuple[LivingStep, ...]
    attachments: tuple[LivingAttachment, ...]
    duration_ms: int | None
    started_ms: int | None
    full_name: str
    allure_url: str
    source_path: str
    source_line: int | None
    source_exists: bool
    status_message: str
    status_trace: str


@dataclass(frozen=True)
class LivingSpecificationsReport:
    """Generated RST plus the referenced binary assets that must be published."""

    source: str
    assets: tuple[LivingAttachment, ...]
