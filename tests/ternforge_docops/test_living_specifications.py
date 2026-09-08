"""Hermetic tests for native Living Specifications presentation."""

from __future__ import annotations

import json
from pathlib import Path

from ternforge_docops._internal.living_specs import (
    publish_living_assets,
    render_living_specifications,
)


def _write_result(path: Path, *, stop: int, status: str) -> None:
    """Write one Allure-shaped BDD result for the same logical example."""
    scenario = "A provider route describes the example traffic image"
    route = "QwenChat"
    rule = "A traffic image produces grounded structured evidence"
    path.write_text(
        json.dumps(
            {
                "name": f"{scenario} — {route}",
                "status": status,
                "description": (
                    "The same image contract should remain valid across supported "
                    "routes.\n\nSpecification: structured_output/images.feature:7"
                ),
                "historyId": "same-example",
                "testCaseId": "same-story",
                "start": stop - 20,
                "stop": stop,
                "fullName": "tests.bdd.test_images#test_image",
                "parameters": [
                    {"name": "_pytest_bdd_example", "value": "{'route': 'QwenChat'}"}
                ],
                "labels": [
                    {"name": "layer", "value": "bdd"},
                    {"name": "epic", "value": "Structured Output"},
                    {"name": "feature", "value": "Structured image understanding"},
                    {
                        "name": "rule",
                        "value": rule,
                    },
                    {
                        "name": "story",
                        "value": "A provider route describes the example traffic image",
                    },
                    {"name": "requirement", "value": "REQ_IMAGE_INPUT"},
                    {"name": "tag", "value": "hermetic"},
                ],
                "steps": [
                    {"name": 'Given the "QwenChat" image route', "status": status},
                    {
                        "name": "When the route analyzes the example traffic image:",
                        "status": status,
                        "attachments": [
                            {
                                "name": "Doc string",
                                "source": "prompt.txt",
                                "type": "text/plain",
                            },
                            {
                                "name": "Input image",
                                "source": "input.png",
                                "type": "image/png",
                            },
                        ],
                    },
                    {
                        "name": "Then the result is a grounded traffic scene",
                        "status": status,
                        "attachments": [
                            {
                                "name": "Result",
                                "source": "result.json",
                                "type": "application/json",
                            }
                        ],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def test_living_specs_render_current_narrative_and_rich_evidence(
    tmp_path: Path,
) -> None:
    """The latest execution becomes one decision-first feature narrative."""
    root = tmp_path / "repo"
    raw = root / "allure-results"
    feature = root / "features" / "structured_output" / "images.feature"
    raw.mkdir(parents=True)
    feature.parent.mkdir(parents=True)
    feature.write_text("Feature: Structured image understanding\n", encoding="utf-8")
    (raw / "prompt.txt").write_text("Describe the attached image.", encoding="utf-8")
    (raw / "result.json").write_text('{"setting":"highway"}', encoding="utf-8")
    (raw / "input.png").write_bytes(b"png")
    _write_result(raw / "old-result.json", stop=100, status="failed")
    _write_result(raw / "current-result.json", stop=200, status="passed")
    result_links = {
        (
            "tests.bdd.test_images#test_image",
            180,
            "A provider route describes the example traffic image — QwenChat",
        ): "test-results/index.html#abc123"
    }

    report = render_living_specifications(root, raw, result_links=result_links)

    assert "Structured image understanding" in report.source
    assert "The same image contract should remain valid" in report.source
    assert ":bdg-success:`Verified` **1/1 passed**" in report.source
    assert ":need:`REQ_IMAGE_INPUT`" in report.source
    assert ".. tab-item:: ✓ QwenChat" in report.source
    assert (
        ":bdg-link-secondary-line:`Execution evidence ↗ "
        "<test-results/index.html#abc123>`" in report.source
    )
    assert ".. card:: Acceptance scenarios" in report.source
    assert (
        ".. card:: Scenario 01 · A provider route describes the example traffic image"
        in report.source
    )
    assert ":bdg-secondary-line:`Rule`" in report.source
    assert ".. container:: living-scenario" not in report.source
    assert ".. container:: living-step" not in report.source
    assert ":class-card: portal-card" not in report.source
    assert "**Executed:**" in report.source
    assert '**Given** the "QwenChat" image route' in report.source
    assert "**When** the route analyzes the example traffic image:" in report.source
    assert "**Prompt**" in report.source
    assert "Describe the attached image." in report.source
    assert "living-json-raw" in report.source
    assert ".. dropdown:: Technical details" in report.source
    assert ".. dropdown:: Gherkin source" in report.source
    assert (
        ".. literalinclude:: ../features/structured_output/images.feature"
        in report.source
    )
    assert [asset.output_name for asset in report.assets] == ["input.png"]


def test_living_specs_publish_only_linked_binary_assets(tmp_path: Path) -> None:
    """Inline JSON/text stay in the page while media is published beside it."""
    root = tmp_path / "repo"
    raw = root / "allure-results"
    feature = root / "features" / "structured_output" / "images.feature"
    raw.mkdir(parents=True)
    feature.parent.mkdir(parents=True)
    feature.write_text("Feature: Structured image understanding\n", encoding="utf-8")
    (raw / "prompt.txt").write_text("prompt", encoding="utf-8")
    (raw / "result.json").write_text("{}", encoding="utf-8")
    (raw / "input.png").write_bytes(b"image-bytes")
    _write_result(raw / "fixture-result.json", stop=200, status="passed")
    report = render_living_specifications(root, raw)
    output = tmp_path / "site"

    publish_living_assets(report, output)

    assets = output / "_living-specs" / "assets"
    assert (assets / "input.png").read_bytes() == b"image-bytes"
    assert not (assets / "prompt.txt").exists()
    assert not (assets / "result.json").exists()


def test_living_specs_without_bdd_evidence_is_explicit(tmp_path: Path) -> None:
    """A normal docs build never invents current verification without a run."""
    raw = tmp_path / "allure-results"
    raw.mkdir()

    report = render_living_specifications(tmp_path, raw)

    assert "No BDD execution evidence was supplied" in report.source
    assert report.assets == ()
