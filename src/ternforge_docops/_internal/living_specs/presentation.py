"""Living Specifications structure and narrative RST presentation."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import PurePosixPath

from ternforge_docops._internal.living_specs.detail import (
    render_example,
    status_icon,
    status_summary,
)
from ternforge_docops._internal.living_specs.models import (
    LivingExample,
    LivingSpecificationPage,
)
from ternforge_docops._internal.living_specs.rst import append_rst, heading, rst_inline

type ScenarioRow = tuple[int, str, str, list[LivingExample]]
type GroupedExamples = dict[str, dict[str, dict[str, dict[str, list[LivingExample]]]]]

_FEATURE_SOURCE_MIN_PARTS = 3


@dataclass(frozen=True)
class _RenderContext:
    """Feature-page link context shared by nested presentation helpers."""

    link_prefix: str
    repository_source_base: str


def _slug(value: str) -> str:
    """Create a stable anchor-safe slug from one narrative label."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug or "behavior"


def _feature_anchor(epic: str, feature: str) -> str:
    """Return the stable Living Specs anchor for one feature."""
    return f"living-feature-{_slug(epic)}-{_slug(feature)}"


def _scenario_anchor(epic: str, feature: str, rule: str, story: str) -> str:
    """Return the stable Living Specs anchor for one acceptance scenario."""
    return (
        f"living-scenario-{_slug(epic)}-{_slug(feature)}-{_slug(rule)}-{_slug(story)}"
    )


def _group_examples(examples: tuple[LivingExample, ...]) -> GroupedExamples:
    """Group examples into the Epic → Feature → Rule → Scenario hierarchy."""
    grouped: GroupedExamples = defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    )
    for example in examples:
        grouped[example.epic][example.feature][example.rule][example.story].append(
            example
        )
    return grouped


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


def _feature_docname(epic: str, feature: str, examples: list[LivingExample]) -> str:
    """Return a stable generated document name, preferring the Gherkin hierarchy."""
    source = next(
        (example.source_path for example in examples if example.source_path), ""
    )
    if source:
        path = PurePosixPath(source)
        if len(path.parts) >= _FEATURE_SOURCE_MIN_PARTS and path.parts[0] == "features":
            return (
                f"specifications/_generated/{_slug(path.parts[1])}/{_slug(path.stem)}"
            )
    return f"specifications/_generated/{_slug(epic)}/{_slug(feature)}"


def _page_prefix(docname: str) -> str:
    """Return the relative URL/source prefix from a generated page to docs root."""
    return "../" * docname.count("/")


def _scenario_rows(
    rules: dict[str, dict[str, list[LivingExample]]],
) -> list[ScenarioRow]:
    """Return deterministically numbered acceptance scenarios for one feature."""
    rows: list[ScenarioRow] = []
    number = 1
    for rule in sorted(rules, key=str.casefold):
        for story in sorted(rules[rule], key=str.casefold):
            rows.append((number, rule, story, rules[rule][story]))
            number += 1
    return rows


def _render_overview(
    lines: list[str],
    examples: tuple[LivingExample, ...],
    pages: tuple[LivingSpecificationPage, ...],
) -> None:
    """Render verification totals and a lightweight capability index."""
    grouped = _group_examples(examples)
    page_by_docname = {page.docname: page for page in pages}

    stories = {
        (example.epic, example.feature, example.rule, example.story)
        for example in examples
    }
    passed = sum(example.status == "passed" for example in examples)

    heading(lines, "Current verification", "-")
    append_rst(lines, 0, ".. grid:: 1 2 4 4")
    append_rst(lines, 3, ":gutter: 2")
    append_rst(lines, 0)
    for title, value in (
        ("Features", str(len(pages))),
        ("Scenarios", str(len(stories))),
        ("Examples", str(len(examples))),
        ("Passing", f"{passed}/{len(examples)}"),
    ):
        append_rst(lines, 3, f".. grid-item-card:: {title}")
        append_rst(lines, 0)
        append_rst(lines, 6, value)
        append_rst(lines, 0)

    heading(lines, "Capabilities by area", "-")
    for epic in sorted(grouped, key=str.casefold):
        lines.extend((f".. _living-specs-area-{_slug(epic)}:", ""))
        heading(lines, epic, "^")
        append_rst(lines, 0, ".. list-table::")
        append_rst(lines, 3, ":header-rows: 1")
        append_rst(lines, 0)
        append_rst(lines, 3, "* - Capability")
        append_rst(lines, 5, "- Outcome")
        append_rst(lines, 5, "- Scenarios")
        append_rst(lines, 5, "- Examples")
        for feature in sorted(grouped[epic], key=str.casefold):
            rules = grouped[epic][feature]
            feature_examples = _feature_examples(rules)
            outcome, count = status_summary(feature_examples)
            scenario_count = len(_scenario_rows(rules))
            docname = _feature_docname(epic, feature, feature_examples)
            page = page_by_docname[docname]
            append_rst(
                lines,
                3,
                f"* - :doc:`{rst_inline(feature)} <{page.docname}>`",
            )
            append_rst(lines, 5, f"- {outcome}")
            append_rst(lines, 5, f"- {scenario_count}")
            append_rst(lines, 5, f"- {count}")
        append_rst(lines, 0)


def _render_story(
    lines: list[str],
    epic: str,
    feature: str,
    row: ScenarioRow,
    *,
    context: _RenderContext,
) -> None:
    """Render one numbered scenario using the stock Sphinx Design disclosure."""
    number, rule, story, examples = row
    ordered = sorted(examples, key=lambda value: value.name.casefold())
    outcome, count = status_summary(ordered)
    lines.extend((f".. _{_scenario_anchor(epic, feature, rule, story)}:", ""))
    append_rst(lines, 0, f".. dropdown:: Scenario {number:02d} · {rst_inline(story)}")
    append_rst(lines, 3, ":open:")
    append_rst(lines, 0)
    append_rst(lines, 3, f"{outcome} **{count}**")
    append_rst(lines, 0)
    requirements = tuple(
        dict.fromkeys(req for example in ordered for req in example.requirements)
    )
    if requirements:
        links = ", ".join(f":need:`{rst_inline(req)}`" for req in requirements)
        append_rst(lines, 3, f"**Verifies:** {links}")
        append_rst(lines, 0)
        append_rst(lines, 3, ".. dropdown:: Contract provenance")
        append_rst(lines, 0)
        append_rst(
            lines,
            6,
            f".. ternforge-contract-provenance:: {','.join(requirements)}",
        )
        append_rst(lines, 0)
    if len(ordered) == 1 and ordered[0].name == "Scenario":
        render_example(
            lines,
            ordered[0],
            3,
            link_prefix=context.link_prefix,
            repository_source_base=context.repository_source_base,
        )
        return
    append_rst(lines, 3, ".. tab-set::")
    append_rst(lines, 0)
    for example in ordered:
        label = f"{status_icon(example.status)} {example.name}"
        append_rst(lines, 6, f".. tab-item:: {rst_inline(label)}")
        append_rst(lines, 0)
        render_example(
            lines,
            example,
            9,
            link_prefix=context.link_prefix,
            repository_source_base=context.repository_source_base,
        )


def _render_scenario_index(
    lines: list[str],
    epic: str,
    feature: str,
    rows: list[ScenarioRow],
) -> None:
    """Render a compact feature-local acceptance-scenario navigation index."""
    append_rst(lines, 0, ".. rubric:: Scenarios")
    append_rst(lines, 0)
    for _, rule, story, examples in rows:
        outcome, count = status_summary(examples)
        anchor = _scenario_anchor(epic, feature, rule, story)
        append_rst(
            lines,
            0,
            f"#. :ref:`{rst_inline(story)} <{anchor}>` — {outcome} {count}",
        )
    append_rst(lines, 0)


def _render_feature_source(
    lines: list[str],
    examples: list[LivingExample],
    *,
    link_prefix: str,
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
        append_rst(lines, 0)
        append_rst(lines, 3, f"``{rst_inline(source)}``")
        append_rst(lines, 0)
        append_rst(lines, 3, f".. literalinclude:: {link_prefix}../{source}")
        append_rst(lines, 6, ":language: gherkin")
        append_rst(lines, 6, ":linenos:")
        append_rst(lines, 0)


def _render_feature_page(
    epic: str,
    feature: str,
    rules: dict[str, dict[str, list[LivingExample]]],
    docname: str,
    repository_source_base: str,
) -> str:
    """Render one self-contained Feature document with Rule/Scenario drill-down."""
    lines = [
        ":orphan:",
        "",
        ":doc:`← Executable specifications </specifications>`",
        "",
    ]
    feature_examples = _feature_examples(rules)
    context = _RenderContext(
        link_prefix=_page_prefix(docname),
        repository_source_base=repository_source_base,
    )
    lines.extend((f".. _{_feature_anchor(epic, feature)}:", ""))
    heading(lines, feature, "=")
    lines.extend((f"**Area:** {rst_inline(epic)}", ""))
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
    lines.extend((f"{outcome} **{count}**", ""))
    rows = _scenario_rows(rules)
    _render_scenario_index(lines, epic, feature, rows)
    current_rule = ""
    for number, rule, story, scenario_examples in rows:
        if rule != current_rule:
            heading(lines, f"Rule · {rule}", "-")
            current_rule = rule
        _render_story(
            lines,
            epic,
            feature,
            (number, rule, story, scenario_examples),
            context=context,
        )
    _render_feature_source(
        lines,
        feature_examples,
        link_prefix=context.link_prefix,
    )
    return "\n".join(lines).rstrip() + "\n"


def render_pages(
    examples: tuple[LivingExample, ...],
    *,
    repository_source_base: str = "",
) -> tuple[LivingSpecificationPage, ...]:
    """Render one generated Sphinx document per Gherkin Feature."""
    grouped = _group_examples(examples)
    pages: list[LivingSpecificationPage] = []
    seen: set[str] = set()
    for epic in sorted(grouped, key=str.casefold):
        for feature in sorted(grouped[epic], key=str.casefold):
            rules = grouped[epic][feature]
            docname = _feature_docname(epic, feature, _feature_examples(rules))
            if docname in seen:
                message = f"Duplicate Living Specifications document name: {docname}"
                raise RuntimeError(message)
            seen.add(docname)
            pages.append(
                LivingSpecificationPage(
                    docname=docname,
                    source=_render_feature_page(
                        epic,
                        feature,
                        rules,
                        docname,
                        repository_source_base,
                    ),
                )
            )
    return tuple(pages)


def render_source(
    examples: tuple[LivingExample, ...],
    pages: tuple[LivingSpecificationPage, ...] | None = None,
) -> str:
    """Render the lightweight Living Specifications index."""
    resolved_pages = pages if pages is not None else render_pages(examples)
    lines: list[str] = []
    _render_overview(lines, examples, resolved_pages)
    return "\n".join(lines).rstrip() + "\n"
