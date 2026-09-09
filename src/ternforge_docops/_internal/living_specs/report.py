"""Living Specifications report orchestration."""

from __future__ import annotations

import shutil
from collections.abc import Mapping
from pathlib import Path

from ternforge_docops._internal.allure.results import ExecutionKey
from ternforge_docops._internal.living_specs.evidence import load_examples
from ternforge_docops._internal.living_specs.models import (
    LivingAttachment,
    LivingExample,
    LivingSpecificationsReport,
)
from ternforge_docops._internal.living_specs.presentation import (
    render_pages,
    render_source,
)

_EMPTY_SOURCE = (
    "No BDD execution evidence was supplied to this build. "
    "Use the portal build with retained Allure results to render "
    "current executable behavior.\n"
)
_INLINE_MEDIA_TYPES = {"application/json", "text/plain"}


def _published_assets(
    examples: tuple[LivingExample, ...],
) -> tuple[LivingAttachment, ...]:
    """Collect unique non-inline attachments that must be copied into the portal."""
    attachments: list[LivingAttachment] = []
    for example in examples:
        attachments.extend(example.attachments)
        for step in example.steps:
            attachments.extend(step.attachments)
    return tuple(
        dict.fromkeys(
            attachment
            for attachment in attachments
            if attachment.source is not None
            and attachment.output_name is not None
            and attachment.media_type not in _INLINE_MEDIA_TYPES
        )
    )


def render_living_specifications(
    root: Path,
    raw_results: Path,
    *,
    result_links: Mapping[ExecutionKey, str] | None = None,
) -> LivingSpecificationsReport:
    """Render current BDD evidence as narrative-first, theme-native RST."""
    examples = load_examples(
        root.resolve(),
        raw_results.resolve(),
        result_links=result_links,
    )
    if not examples:
        return LivingSpecificationsReport(source=_EMPTY_SOURCE, assets=())
    pages = render_pages(examples)
    return LivingSpecificationsReport(
        source=render_source(examples, pages),
        assets=_published_assets(examples),
        pages=pages,
    )


def publish_living_assets(
    report: LivingSpecificationsReport, output_root: Path
) -> None:
    """Publish only assets referenced by the generated Living Specifications report."""
    target = output_root / "_living-specs" / "assets"
    shutil.rmtree(output_root / "_living-specs", ignore_errors=True)
    if not report.assets:
        return
    target.mkdir(parents=True, exist_ok=True)
    for asset in report.assets:
        if asset.source is not None and asset.output_name is not None:
            shutil.copy2(asset.source, target / asset.output_name)
