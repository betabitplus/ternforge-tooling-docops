"""Hermetic Allure presentation tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ternforge_docops._internal.allure import curate_results, generate_reports


def _write_result(
    path: Path,
    *,
    name: str,
    layer: str,
    requirement: str,
    attachment: str,
) -> None:
    path.write_text(
        json.dumps(
            {
                "name": name,
                "status": "passed",
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


def test_curate_results_uses_allure_labels_and_needs_titles(tmp_path: Path) -> None:
    """Curation never joins Allure results back to JUnit testcase names."""
    raw = tmp_path / "raw"
    curated = tmp_path / "curated"
    bdd = tmp_path / "bdd"
    raw.mkdir()
    needs_json = tmp_path / "needs.json"
    needs_json.write_text(
        json.dumps(
            {
                "current_version": "1",
                "versions": {
                    "1": {
                        "needs": {
                            "REQ_UNIT": {"title": "Unit contract"},
                            "REQ_BDD": {"title": "BDD contract"},
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    _write_result(
        raw / "unit-result.json",
        name="test_raw_python_name",
        layer="unit",
        requirement="REQ_UNIT",
        attachment="unit-attachment.txt",
    )
    _write_result(
        raw / "bdd-result.json",
        name="Human BDD scenario",
        layer="bdd",
        requirement="REQ_BDD",
        attachment="bdd-attachment.txt",
    )
    (raw / "unit-attachment.txt").write_text("unit evidence", encoding="utf-8")
    (raw / "bdd-attachment.txt").write_text("bdd evidence", encoding="utf-8")
    (raw / "fixture-container.json").write_text("{}", encoding="utf-8")

    curate_results(
        raw,
        needs_json=needs_json,
        curated_results=curated,
        bdd_results=bdd,
    )

    unit = json.loads((curated / "unit-result.json").read_text(encoding="utf-8"))
    bdd_result = json.loads((bdd / "bdd-result.json").read_text(encoding="utf-8"))
    unit_labels = {(label["name"], label["value"]) for label in unit["labels"]}
    bdd_labels = {(label["name"], label["value"]) for label in bdd_result["labels"]}
    assert unit["name"] == "test_raw_python_name"
    assert ("requirement_view", "REQ_UNIT — Unit contract") in unit_labels
    assert ("requirement_view", "REQ_BDD — BDD contract") in bdd_labels
    assert (curated / "unit-attachment.txt").read_text() == "unit evidence"
    assert (bdd / "bdd-attachment.txt").read_text() == "bdd evidence"
    assert not (curated / "fixture-container.json").exists()
    assert not (bdd / "unit-result.json").exists()


def test_generate_reports_delegates_html_to_allure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DocOps selects perspectives while Allure owns the generated HTML shell."""
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
    bdd = tmp_path / "bdd"
    curated.mkdir()
    bdd.mkdir()

    reports = generate_reports(
        curated_results=curated,
        bdd_results=bdd,
        output_root=tmp_path / "reports",
    )

    assert set(reports) == {"bdd", "requirements", "all"}
    assert len(commands) == 3
    assert all("--single-file" in command for command in commands)
    assert all("--theme" not in command for command in commands)
    assert commands[0][commands[0].index("--group-by") + 1] == "epic,feature,rule"
    assert commands[1][commands[1].index("--group-by") + 1] == (
        "requirement_view,layer"
    )
    assert commands[2][commands[2].index("--group-by") + 1] == (
        "layer,parentSuite,suite"
    )
