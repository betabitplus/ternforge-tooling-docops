"""Evidence-detail RST primitives for Living Specifications."""

from __future__ import annotations

import html
from datetime import UTC, datetime

from ternforge_docops._internal.living_specs.models import (
    LivingAttachment,
    LivingExample,
    LivingStep,
)

_TECHNICAL_ATTACHMENT_NAMES = {"log", "stderr", "stdout"}


def rst_inline(value: str) -> str:
    """Escape a short value for inline RST text."""
    return (
        value.replace("\\", "\\\\")
        .replace("`", "\\`")
        .replace("*", "\\*")
        .replace("|", "\\|")
    )


def heading(lines: list[str], title: str, marker: str) -> None:
    """Append one RST section heading."""
    lines.extend((title, marker * max(3, len(title)), ""))


def append_rst(lines: list[str], indent: int, text: str = "") -> None:
    """Append one optionally-indented RST line."""
    lines.append(f"{' ' * indent}{text}" if text else "")


def _code_block(
    lines: list[str], indent: int, language: str, content: str, css: str = ""
) -> None:
    """Append a literal code block with optional presentation class."""
    append_rst(lines, indent, f".. code-block:: {language}")
    if css:
        append_rst(lines, indent + 3, f":class: {css}")
    append_rst(lines, 0)
    for line in content.splitlines() or [""]:
        append_rst(lines, indent + 3, line)
    append_rst(lines, 0)


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


def _asset_url(attachment: LivingAttachment) -> str:
    """Return the published relative URL for one retained binary attachment."""
    if attachment.output_name is None:
        return ""
    return f"_living-specs/assets/{html.escape(attachment.output_name, quote=True)}"


def _render_attachment(
    lines: list[str], attachment: LivingAttachment, indent: int
) -> None:
    """Render retained evidence inline using a media-appropriate representation."""
    label = "Prompt" if attachment.name == "Doc string" else attachment.name
    append_rst(lines, indent, f"**{rst_inline(label)}**")
    append_rst(lines, 0)
    if attachment.source is None:
        append_rst(lines, indent, "*Captured attachment is unavailable.*")
        append_rst(lines, 0)
        return
    if attachment.media_type == "application/json":
        _code_block(
            lines,
            indent,
            "json",
            attachment.source.read_text(encoding="utf-8", errors="replace"),
            "living-json-raw",
        )
        return
    if attachment.media_type == "text/plain":
        _code_block(
            lines,
            indent,
            "text",
            attachment.source.read_text(encoding="utf-8", errors="replace"),
        )
        return
    url = _asset_url(attachment)
    label_html = html.escape(label)
    if attachment.media_type.startswith("image/"):
        raw = f'<img class="living-media living-image" src="{url}" alt="{label_html}">'
    elif attachment.media_type.startswith("video/"):
        media_type = html.escape(attachment.media_type, quote=True)
        raw = (
            '<video class="living-media living-video" controls preload="metadata">'
            f'<source src="{url}" type="{media_type}">'
            f'<a href="{url}">Open {label_html}</a>'
            "</video>"
        )
    elif attachment.media_type == "application/pdf":
        raw = (
            '<object class="living-media living-pdf" data="'
            f'{url}" type="application/pdf">'
            f'<a href="{url}">Open {label_html}</a>'
            "</object>"
        )
    else:
        raw = f'<a class="living-download" href="{url}">Open {label_html}</a>'
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


def _render_step(lines: list[str], step: LivingStep, indent: int) -> None:
    """Render one executed BDD step with non-forensic attachments beside it."""
    keyword, text = _step_parts(step.name)
    sentence = f"**{keyword}** {rst_inline(text)}".rstrip()
    append_rst(lines, indent, sentence)
    append_rst(lines, 0)
    for attachment in step.attachments:
        if attachment.name.casefold() in _TECHNICAL_ATTACHMENT_NAMES:
            continue
        _render_attachment(lines, attachment, indent)


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
        _code_block(lines, body, "text", example.status_message)
    if example.status_trace:
        append_rst(lines, body, "**Failure trace**")
        append_rst(lines, 0)
        _code_block(lines, body, "text", example.status_trace)


def _render_technical_attachments(
    lines: list[str], example: LivingExample, body: int
) -> None:
    """Render root and technical step attachments inside the forensic disclosure."""
    for attachment in example.attachments:
        _render_attachment(lines, attachment, body)
    for step in example.steps:
        for attachment in step.attachments:
            if attachment.name.casefold() in _TECHNICAL_ATTACHMENT_NAMES:
                _render_attachment(lines, attachment, body)


def _render_technical(lines: list[str], example: LivingExample, indent: int) -> None:
    """Render the collapsed forensic disclosure for one current example."""
    append_rst(lines, indent, ".. dropdown:: Technical details")
    append_rst(lines, indent + 3, ":class-container: living-technical-details")
    append_rst(lines, 0)
    body = indent + 3
    _render_technical_metadata(lines, example, body)
    _render_technical_failures(lines, example, body)
    _render_technical_attachments(lines, example, body)


def render_example(lines: list[str], example: LivingExample, indent: int) -> None:
    """Render one current BDD example and its evidence."""
    if example.allure_url:
        append_rst(
            lines,
            indent,
            f":bdg-link-secondary-line:`Execution evidence ↗ <{example.allure_url}>`",
        )
        append_rst(lines, 0)
    if example.status != "passed" and example.status_message:
        append_rst(
            lines, indent, f"**Attention:** {rst_inline(example.status_message)}"
        )
        append_rst(lines, 0)
    for step in example.steps:
        _render_step(lines, step, indent)
    _render_technical(lines, example, indent)
