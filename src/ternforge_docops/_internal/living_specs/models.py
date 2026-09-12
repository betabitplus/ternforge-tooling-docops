"""Data model for native Living Specifications presentation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ternforge_docops._internal.verification.assurance import VerificationBoundary


@dataclass(frozen=True)
class LivingAttachment:
    """One retained attachment referenced by an Allure result or step."""

    name: str
    media_type: str
    source: Path | None
    output_name: str | None


@dataclass(frozen=True)
class LivingImplementation:
    """Exact Python binding source captured for one executed BDD step."""

    keyword: str
    text: str
    function: str
    path: str
    start_line: int
    end_line: int
    source: str


@dataclass(frozen=True)
class LivingContract:
    """One live schema/callable contract captured by the executing test."""

    name: str
    kind: str
    qualified_name: str
    description: str
    signature: str
    schema: object | None


@dataclass(frozen=True)
class LivingStep:
    """One executed Given/When/Then step with retained evidence."""

    name: str
    status: str
    attachments: tuple[LivingAttachment, ...]
    implementation: LivingImplementation | None = None
    contracts: tuple[LivingContract, ...] = ()


LivingVerificationBoundary = VerificationBoundary


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
    boundary: LivingVerificationBoundary | None = None
    nodeid: str = ""


@dataclass(frozen=True)
class LivingSpecificationPage:
    """One generated feature-level Living Specifications document."""

    docname: str
    source: str


@dataclass(frozen=True)
class LivingSpecificationsReport:
    """Generated index/pages plus referenced binary assets that must be published."""

    source: str
    assets: tuple[LivingAttachment, ...]
    pages: tuple[LivingSpecificationPage, ...] = ()
