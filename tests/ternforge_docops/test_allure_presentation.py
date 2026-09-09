"""Hermetic Allure presentation tests."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from ternforge_docops._internal.allure import (
    curate_results,
    extract_result_links,
    generate_report,
)


def _write_result(
    path: Path,
    *,
    name: str,
    layer: str,
    requirement: str,
    attachment: str,
    history_id: str,
    stop: int,
) -> None:
    path.write_text(
        json.dumps(
            {
                "name": name,
                "status": "passed",
                "historyId": history_id,
                "start": stop - 10,
                "stop": stop,
                "labels": [
                    {"name": "layer", "value": layer},
                    {"name": "requirement", "value": requirement},
                ],
                "steps": [
                    {
                        "name": "observe",
                        "status": "passed",
                        "attachments": [
                            {
                                "name": "evidence",
                                "source": attachment,
                                "type": "text/plain",
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_curate_results_keeps_only_current_execution_and_referenced_evidence(
    tmp_path: Path,
) -> None:
    """The forensic view is current-only and does not copy fixture or stale evidence."""
    raw = tmp_path / "raw"
    curated = tmp_path / "curated"
    raw.mkdir()
    _write_result(
        raw / "old-result.json",
        name="scenario",
        layer="bdd",
        requirement="REQ_BDD",
        attachment="old.txt",
        history_id="scenario-history",
        stop=100,
    )
    _write_result(
        raw / "new-result.json",
        name="scenario",
        layer="bdd",
        requirement="REQ_BDD",
        attachment="new.txt",
        history_id="scenario-history",
        stop=200,
    )
    _write_result(
        raw / "unit-result.json",
        name="unit test",
        layer="unit",
        requirement="REQ_UNIT",
        attachment="unit.txt",
        history_id="unit-history",
        stop=150,
    )
    for name in ("old.txt", "new.txt", "unit.txt"):
        (raw / name).write_text(name, encoding="utf-8")
    (raw / "fixture-container.json").write_text("{}", encoding="utf-8")

    curate_results(raw, curated_results=curated)

    assert not (curated / "old-result.json").exists()
    assert not (curated / "old.txt").exists()
    assert (curated / "new-result.json").is_file()
    assert (curated / "new.txt").read_text() == "new.txt"
    assert (curated / "unit-result.json").is_file()
    assert (curated / "unit.txt").read_text() == "unit.txt"
    assert not (curated / "fixture-container.json").exists()
    current = json.loads((curated / "new-result.json").read_text(encoding="utf-8"))
    labels = {(label["name"], label["value"]) for label in current["labels"]}
    assert ("requirement", "REQ_BDD") in labels
    assert all(name != "requirement_view" for name, _ in labels)


def test_curate_results_excludes_binary_evidence_from_single_file_allure(
    tmp_path: Path,
) -> None:
    """Binary evidence stays out of Allure while text diagnostics remain available."""
    raw = tmp_path / "raw"
    curated = tmp_path / "curated"
    raw.mkdir()
    result_path = raw / "scenario-result.json"
    _write_result(
        result_path,
        name="scenario",
        layer="bdd",
        requirement="REQ_BDD",
        attachment="step.txt",
        history_id="scenario-history",
        stop=200,
    )
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["attachments"] = [
        {"name": "image", "source": "image.png", "type": "image/png"},
        {"name": "video", "source": "video.mp4", "type": "video/mp4"},
        {"name": "pdf", "source": "paper.pdf", "type": "application/pdf"},
        {"name": "json", "source": "result.json", "type": "application/json"},
        {
            "name": "BDD implementation",
            "source": "implementation.json",
            "type": "application/vnd.ternforge.bdd-implementation+json",
        },
        {
            "name": "Public contract",
            "source": "contract.json",
            "type": "application/vnd.ternforge.contract+json",
        },
        {"name": "trace", "source": "trace.txt", "type": "text/plain; charset=utf-8"},
    ]
    result_path.write_text(json.dumps(result), encoding="utf-8")
    for name in (
        "step.txt",
        "image.png",
        "video.mp4",
        "paper.pdf",
        "result.json",
        "implementation.json",
        "contract.json",
        "trace.txt",
    ):
        (raw / name).write_bytes(name.encode())

    curate_results(raw, curated_results=curated)

    current = json.loads((curated / result_path.name).read_text(encoding="utf-8"))
    retained = {attachment["source"] for attachment in current["attachments"]}
    assert retained == {"result.json", "trace.txt"}
    assert (curated / "step.txt").is_file()
    assert (curated / "result.json").is_file()
    assert (curated / "trace.txt").is_file()
    assert not (curated / "implementation.json").exists()
    assert not (curated / "contract.json").exists()
    assert not (curated / "image.png").exists()
    assert not (curated / "video.mp4").exists()
    assert not (curated / "paper.pdf").exists()


def test_generate_report_delegates_forensic_html_to_allure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DocOps selects one forensic perspective while Allure owns the HTML shell."""
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, check: bool) -> None:
        assert check is True
        commands.append(command)
        output = Path(command[command.index("--output") + 1])
        output.mkdir(parents=True)
        (output / "index.html").write_text('<div id="app"></div>', encoding="utf-8")

    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/npx")
    monkeypatch.setattr("subprocess.run", fake_run)
    curated = tmp_path / "curated"
    curated.mkdir()

    report = generate_report(
        curated_results=curated,
        output=tmp_path / "report",
    )

    assert report == tmp_path / "report" / "index.html"
    assert len(commands) == 1
    command = commands[0]
    assert "--single-file" in command
    assert "--theme" not in command
    assert command[command.index("--group-by") + 1] == "layer,parentSuite,suite"
    assert command[command.index("--report-name") + 1] == "All test results"


def test_extract_result_links_uses_allure_ids(tmp_path: Path) -> None:
    """Living Specs can deep-link to the exact result rendered by pinned Allure 3."""
    result = {
        "name": "scenario — QwenChat",
        "fullName": "tests.bdd.test_example#test_scenario",
        "start": 123,
        "status": "passed",
    }
    payload = base64.b64encode(json.dumps(result).encode()).decode()
    report = tmp_path / "index.html"
    report.write_text(
        f'<script>d("data/test-results/abc123.json","{payload}")</script>',
        encoding="utf-8",
    )

    links = extract_result_links(report)

    assert links == {
        (
            "tests.bdd.test_example#test_scenario",
            123,
            "scenario — QwenChat",
        ): "test-results/index.html#abc123"
    }
