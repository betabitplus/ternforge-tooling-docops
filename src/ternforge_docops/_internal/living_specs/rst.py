"""Small reStructuredText primitives shared by Living Specifications renderers."""

from __future__ import annotations


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


def code_block(
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
