"""Evidence-detail RST primitives for Living Specifications."""

from __future__ import annotations

import html
from datetime import UTC, datetime

from ternforge_docops._internal.living_specs.execution_detail import (
    implementation_url,
    render_executable_usage,
    render_observed_outcome,
    render_public_contract,
)
from ternforge_docops._internal.living_specs.models import (
    LivingAttachment,
    LivingExample,
    LivingStep,
    LivingVerificationBoundary,
)
from ternforge_docops._internal.living_specs.rst import (
    append_rst,
    code_block,
    rst_inline,
)
from ternforge_docops._internal.verification.assurance import boundary_interaction_text

_TECHNICAL_ATTACHMENT_NAMES = {"log", "stderr", "stdout"}


def status_summary(values: list[LivingExample]) -> tuple[str, str]:
    """Summarize verification outcome using stock Sphinx Design badges."""
    total = len(values)
    passed = sum(value.status == "passed" for value in values)
    if total and passed == total:
        return ":bdg-success:`Verified`", f"{passed}/{total} passed"
    if any(value.status in {"failed", "broken"} for value in values):
        return ":bdg-danger:`Failing`", f"{passed}/{total} passed"
    if any(value.status == "skipped" for value in values):
        return ":bdg-warning:`Incomplete`", f"{passed}/{total} passed"
    return ":bdg-secondary:`Unknown`", f"{passed}/{total} passed"


def status_icon(status: str) -> str:
    """Return a compact status marker for one example."""
    return {
        "passed": "✓",
        "failed": "✗",
        "broken": "✗",
        "skipped": "○",
    }.get(status, "?")


def _asset_url(attachment: LivingAttachment, link_prefix: str) -> str:
    """Return the published relative URL for one retained binary attachment."""
    if attachment.output_name is None:
        return ""
    return (
        f"{link_prefix}_living-specs/assets/"
        f"{html.escape(attachment.output_name, quote=True)}"
    )


def _render_attachment(
    lines: list[str],
    attachment: LivingAttachment,
    indent: int,
    link_prefix: str,
) -> None:
    """Render retained evidence inline using a media-appropriate representation."""
    label = "Prompt" if attachment.name == "Doc string" else attachment.name
    if attachment.source is None:
        append_rst(lines, indent, f"**{rst_inline(label)}**")
        append_rst(lines, 0)
        append_rst(lines, indent, "*Captured attachment is unavailable.*")
        append_rst(lines, 0)
        return
    if attachment.media_type == "application/json":
        render_observed_outcome(lines, attachment, indent)
        append_rst(lines, indent, ".. dropdown:: Raw captured result")
        append_rst(lines, 0)
        code_block(
            lines,
            indent + 3,
            "json",
            attachment.source.read_text(encoding="utf-8", errors="replace"),
        )
        return
    append_rst(lines, indent, f"**{rst_inline(label)}**")
    append_rst(lines, 0)
    if attachment.media_type == "text/plain":
        code_block(
            lines,
            indent,
            "text",
            attachment.source.read_text(encoding="utf-8", errors="replace"),
        )
        return
    url = _asset_url(attachment, link_prefix)
    label_html = html.escape(label)
    if attachment.media_type.startswith("image/"):
        append_rst(lines, indent, f".. image:: {url}")
        append_rst(lines, indent + 3, f":alt: {rst_inline(label)}")
        append_rst(lines, indent + 3, ":class: living-image")
        append_rst(lines, 0)
        return
    if attachment.media_type.startswith("video/"):
        media_type = html.escape(attachment.media_type, quote=True)
        raw = (
            '<video class="living-video" controls preload="metadata">'
            f'<source src="{url}" type="{media_type}">'
            f'<a href="{url}">Open {label_html}</a>'
            "</video>"
        )
    elif attachment.media_type == "application/pdf":
        raw = (
            '<object class="living-pdf" data="'
            f'{url}" type="application/pdf">'
            f'<a href="{url}">Open {label_html}</a>'
            "</object>"
        )
    else:
        append_rst(lines, indent, f"`Open {rst_inline(label)} <{url}>`__")
        append_rst(lines, 0)
        return
    append_rst(lines, indent, ".. raw:: html")
    append_rst(lines, 0)
    append_rst(lines, indent + 3, raw)
    append_rst(lines, 0)


def _step_parts(name: str) -> tuple[str, str]:
    """Split a BDD step into keyword and human-readable sentence text."""
    first, separator, rest = name.partition(" ")
    if first in {"Given", "When", "Then", "And", "But"}:
        return first, rest if separator else ""
    return "Step", name


def _render_step(
    lines: list[str],
    step: LivingStep,
    indent: int,
    link_prefix: str,
    repository_source_base: str,
) -> None:
    """Render one executed BDD step with evidence and implementation provenance."""
    keyword, text = _step_parts(step.name)
    sentence = f"**{keyword}** {rst_inline(text)}".rstrip()
    append_rst(lines, indent, sentence)
    if step.implementation is not None:
        source_url = implementation_url(step.implementation, repository_source_base)
        if source_url:
            append_rst(
                lines,
                indent,
                f":bdg-link-secondary-line:`Implementation ↗ <{source_url}>`",
            )
    append_rst(lines, 0)
    for attachment in step.attachments:
        if attachment.name.casefold() in _TECHNICAL_ATTACHMENT_NAMES:
            continue
        _render_attachment(lines, attachment, indent, link_prefix)
    if keyword == "When" and step.implementation is not None:
        render_executable_usage(
            lines,
            step.implementation,
            indent,
            repository_source_base,
        )
    render_public_contract(lines, step.contracts, indent)


def render_verification_boundary(
    lines: list[str],
    boundary: LivingVerificationBoundary,
    indent: int,
) -> None:
    """Render the tested boundary without turning it into a status report."""
    append_rst(lines, indent, ".. card:: Verification boundary")
    append_rst(lines, 0)
    body = indent + 3
    append_rst(lines, body, f"**Path:** ``{rst_inline(boundary.path)}``")
    append_rst(lines, 0)
    if boundary.provenance != "source-derived fallback":
        append_rst(
            lines,
            body,
            (
                "**Execution envelope:** "
                f":bdg-secondary:`Process · {rst_inline(boundary.process)}` "
                f":bdg-secondary:`Network · {rst_inline(boundary.network)}` "
                f":bdg-secondary:`Filesystem · {rst_inline(boundary.filesystem)}` "
                f":bdg-secondary:`External · {rst_inline(boundary.external)}`"
            ),
        )
        append_rst(lines, 0)
    append_rst(lines, body, f"* **Real path:** {rst_inline(boundary.real_path)}")
    append_rst(lines, body, f"* **Substitute:** {rst_inline(boundary.substitute)}")
    append_rst(lines, body, f"* **Not covered:** {rst_inline(boundary.not_covered)}")
    append_rst(lines, 0)
    if boundary.interactions:
        append_rst(lines, body, "**Captured boundary interactions:**")
        append_rst(lines, 0)
        for interaction in boundary.interactions:
            append_rst(
                lines,
                body,
                f"* ``{rst_inline(boundary_interaction_text(interaction))}``",
            )
        append_rst(lines, 0)
    append_rst(lines, body, ".. dropdown:: How this scenario establishes the proof")
    append_rst(lines, 0)
    detail = body + 3
    injected = (
        boundary.injected_condition or "No separate injected condition is declared."
    )
    observed = boundary.observed_proof or "The scenario's explicit Then assertions."
    append_rst(lines, detail, f"**Injected condition:** {rst_inline(injected)}")
    append_rst(lines, 0)
    append_rst(lines, detail, f"**Observed proof:** {rst_inline(observed)}")
    append_rst(lines, 0)
    append_rst(lines, detail, f"**Boundary basis:** {boundary.provenance}")
    append_rst(lines, 0)


def _render_technical_metadata(
    lines: list[str], example: LivingExample, body: int
) -> None:
    """Render forensic execution metadata for one BDD example."""
    append_rst(lines, body, f"**Status:** ``{example.status}``")
    append_rst(lines, 0)
    if example.started_ms is not None:
        executed = datetime.fromtimestamp(example.started_ms / 1000, tz=UTC).isoformat(
            timespec="seconds"
        )
        append_rst(lines, body, f"**Executed:** ``{executed.replace('+00:00', 'Z')}``")
        append_rst(lines, 0)
    if example.duration_ms is not None:
        append_rst(lines, body, f"**Duration:** {example.duration_ms} ms")
        append_rst(lines, 0)
    if example.full_name:
        append_rst(lines, body, f"**Pytest node:** ``{rst_inline(example.full_name)}``")
        append_rst(lines, 0)
    if example.tags:
        tags = ", ".join(f"``{rst_inline(tag)}``" for tag in example.tags)
        append_rst(lines, body, f"**Tags:** {tags}")
        append_rst(lines, 0)
    if example.source_path:
        location = example.source_path
        if example.source_line is not None:
            location = f"{location}:{example.source_line}"
        append_rst(lines, body, f"**Specification:** ``{rst_inline(location)}``")
        append_rst(lines, 0)


def _render_technical_failures(
    lines: list[str], example: LivingExample, body: int
) -> None:
    """Render retained failure diagnostics when the execution did not pass."""
    if example.status_message:
        append_rst(lines, body, "**Failure message**")
        append_rst(lines, 0)
        code_block(lines, body, "text", example.status_message)
    if example.status_trace:
        append_rst(lines, body, "**Failure trace**")
        append_rst(lines, 0)
        code_block(lines, body, "text", example.status_trace)


def _render_technical_attachments(
    lines: list[str], example: LivingExample, body: int, link_prefix: str
) -> None:
    """Render root and technical step attachments inside the forensic disclosure."""
    for attachment in example.attachments:
        _render_attachment(lines, attachment, body, link_prefix)
    for step in example.steps:
        for attachment in step.attachments:
            if attachment.name.casefold() in _TECHNICAL_ATTACHMENT_NAMES:
                _render_attachment(lines, attachment, body, link_prefix)


def _render_technical(
    lines: list[str], example: LivingExample, indent: int, link_prefix: str
) -> None:
    """Render the collapsed forensic disclosure for one current example."""
    append_rst(lines, indent, ".. dropdown:: Technical details")
    append_rst(lines, indent + 3, ":class-container: living-technical-details")
    append_rst(lines, 0)
    body = indent + 3
    _render_technical_metadata(lines, example, body)
    _render_technical_failures(lines, example, body)
    _render_technical_attachments(lines, example, body, link_prefix)


def render_example(
    lines: list[str],
    example: LivingExample,
    indent: int,
    *,
    link_prefix: str = "",
    repository_source_base: str = "",
) -> None:
    """Render one current BDD example and its evidence."""
    if example.allure_url:
        append_rst(
            lines,
            indent,
            f":bdg-link-secondary-line:`Execution evidence ↗ "
            f"<{link_prefix}{example.allure_url}>`",
        )
        append_rst(lines, 0)
    if example.status != "passed" and example.status_message:
        append_rst(
            lines, indent, f"**Attention:** {rst_inline(example.status_message)}"
        )
        append_rst(lines, 0)
    for step in example.steps:
        _render_step(
            lines,
            step,
            indent,
            link_prefix,
            repository_source_base,
        )
    _render_technical(lines, example, indent, link_prefix)
