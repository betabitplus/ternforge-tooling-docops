"""Living Specifications structure and narrative RST presentation."""

from __future__ import annotations

import re
from collections import defaultdict

from ternforge_docops._internal.living_specs.detail import (
    append_rst,
    heading,
    render_example,
    rst_inline,
    status_icon,
    status_summary,
)
from ternforge_docops._internal.living_specs.models import LivingExample


def _slug(value: str) -> str:
    """Create a stable anchor-safe slug from one narrative label."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug or "behavior"


def _feature_anchor(epic: str, feature: str) -> str:
    """Return the stable Living Specs anchor for one feature."""
    return f"living-feature-{_slug(epic)}-{_slug(feature)}"


def _group_examples(
    examples: tuple[LivingExample, ...],
) -> dict[str, dict[str, dict[str, dict[str, list[LivingExample]]]]]:
    """Group examples into the Epic → Feature → Rule → Scenario hierarchy."""
    grouped: dict[str, dict[str, dict[str, dict[str, list[LivingExample]]]]] = (
        defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))
    )
    for example in examples:
        grouped[example.epic][example.feature][example.rule][example.story].append(
            example
        )
    return grouped


def _render_overview(lines: list[str], examples: tuple[LivingExample, ...]) -> None:
    """Render decision-first verification totals and the clickable feature overview."""
    features: dict[tuple[str, str], list[LivingExample]] = defaultdict(list)
    stories: set[tuple[str, str, str, str]] = set()
    for example in examples:
        features[(example.epic, example.feature)].append(example)
        stories.add((example.epic, example.feature, example.rule, example.story))
    passed = sum(example.status == "passed" for example in examples)

    heading(lines, "Current verification", "-")
    append_rst(lines, 0, ".. grid:: 1 2 4 4")
    append_rst(lines, 3, ":gutter: 2")
    append_rst(lines, 0)
    for title, value in (
        ("Features", str(len(features))),
        ("Scenarios", str(len(stories))),
        ("Examples", str(len(examples))),
        ("Passing", f"{passed}/{len(examples)}"),
    ):
        append_rst(lines, 3, f".. grid-item-card:: {title}")
        append_rst(lines, 6, ":class-card: portal-card")
        append_rst(lines, 0)
        append_rst(lines, 6, value)
        append_rst(lines, 0)

    heading(lines, "Feature overview", "-")
    append_rst(lines, 0, ".. list-table::")
    append_rst(lines, 3, ":header-rows: 1")
    append_rst(lines, 3, ":class: living-feature-overview")
    append_rst(lines, 0)
    append_rst(lines, 3, "* - Area")
    append_rst(lines, 5, "- Capability")
    append_rst(lines, 5, "- Outcome")
    append_rst(lines, 5, "- Examples")
    for (epic, feature), values in sorted(features.items(), key=lambda item: item[0]):
        outcome, count = status_summary(values)
        anchor = _feature_anchor(epic, feature)
        append_rst(lines, 3, f"* - {rst_inline(epic)}")
        append_rst(lines, 5, f"- :ref:`{rst_inline(feature)} <{anchor}>`")
        append_rst(lines, 5, f"- {outcome}")
        append_rst(lines, 5, f"- {count}")
    append_rst(lines, 0)


def _render_story(
    lines: list[str],
    story: str,
    examples: list[LivingExample],
) -> None:
    """Render one scenario and its current concrete examples."""
    ordered = sorted(examples, key=lambda value: value.name.casefold())
    outcome, count = status_summary(ordered)
    append_rst(lines, 0, f"**Scenario:** {rst_inline(story)}")
    append_rst(lines, 0)
    append_rst(lines, 0, f"**Current verification:** {outcome} · {count}")
    append_rst(lines, 0)
    requirements = tuple(
        dict.fromkeys(req for example in ordered for req in example.requirements)
    )
    if requirements:
        links = ", ".join(f":need:`{rst_inline(req)}`" for req in requirements)
        append_rst(lines, 0, f"**Verifies:** {links}")
        append_rst(lines, 0)
    if len(ordered) == 1 and ordered[0].name == "Scenario":
        render_example(lines, ordered[0], 0)
        return
    append_rst(lines, 0, ".. tab-set::")
    append_rst(lines, 0)
    for example in ordered:
        label = f"{status_icon(example.status)} {example.name}"
        append_rst(lines, 3, f".. tab-item:: {rst_inline(label)}")
        append_rst(lines, 0)
        render_example(lines, example, 6)


def _render_feature_source(
    lines: list[str],
    examples: list[LivingExample],
) -> None:
    """Render exact Gherkin source as an optional drill-down for one feature."""
    sources = tuple(
        dict.fromkeys(
            example.source_path for example in examples if example.source_path
        )
    )
    for source in sources:
        exists = any(
            example.source_path == source and example.source_exists
            for example in examples
        )
        if not exists:
            continue
        append_rst(lines, 0, ".. dropdown:: Gherkin source")
        append_rst(lines, 3, ":class-container: living-source")
        append_rst(lines, 0)
        append_rst(lines, 3, f"``{rst_inline(source)}``")
        append_rst(lines, 0)
        append_rst(lines, 3, f".. literalinclude:: ../{source}")
        append_rst(lines, 6, ":language: gherkin")
        append_rst(lines, 6, ":linenos:")
        append_rst(lines, 0)


def _feature_examples(
    rules: dict[str, dict[str, list[LivingExample]]],
) -> list[LivingExample]:
    """Flatten all examples belonging to one feature."""
    return [
        example
        for stories in rules.values()
        for examples in stories.values()
        for example in examples
    ]


def _render_feature(
    lines: list[str],
    epic: str,
    feature: str,
    rules: dict[str, dict[str, list[LivingExample]]],
) -> None:
    """Render one feature summary, rules, scenarios, and source disclosure."""
    feature_examples = _feature_examples(rules)
    lines.extend((f".. _{_feature_anchor(epic, feature)}:", ""))
    heading(lines, feature, "~")
    description = next(
        (
            example.feature_description
            for example in feature_examples
            if example.feature_description
        ),
        "",
    )
    if description:
        lines.extend((rst_inline(description), ""))
    outcome, count = status_summary(feature_examples)
    lines.extend((f"**Current verification:** {outcome} · {count}", ""))
    for rule in sorted(rules, key=str.casefold):
        lines.extend((f".. rubric:: Rule — {rst_inline(rule)}", ""))
        for story in sorted(rules[rule], key=str.casefold):
            _render_story(lines, story, rules[rule][story])
    _render_feature_source(lines, feature_examples)


def render_source(examples: tuple[LivingExample, ...]) -> str:
    """Render normalized BDD examples into narrative-first RST."""
    lines: list[str] = []
    _render_overview(lines, examples)
    grouped = _group_examples(examples)
    for epic in sorted(grouped, key=str.casefold):
        heading(lines, epic, "-")
        for feature in sorted(grouped[epic], key=str.casefold):
            _render_feature(lines, epic, feature, grouped[epic][feature])
    return "\n".join(lines).rstrip() + "\n"
