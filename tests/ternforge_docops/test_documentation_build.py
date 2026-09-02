"""Tests for documentation presentation orchestration."""

from __future__ import annotations

from pathlib import Path

import pytest

from ternforge_docops._internal.documentation import service


def test_build_html_runs_only_sphinx(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DocOps builds presentation but never executes the project test runner."""
    docs = tmp_path / "docs"
    docs.mkdir()
    output = tmp_path / "site"
    commands: list[list[str]] = []

    def fake_build_main(arguments: list[str]) -> int:
        assert Path.cwd() == tmp_path
        commands.append(arguments)
        return 0

    monkeypatch.setattr(service, "build_main", fake_build_main)

    result = service.build_html(tmp_path, docs=docs, output=output)

    assert result == output
    assert len(commands) == 1
    command = commands[0]
    assert command[command.index("-b") + 1] == "html"
    assert "pytest" not in command


def test_build_dossier_delegates_to_simplepdf(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PDF generation remains an upstream Sphinx builder responsibility."""
    docs = tmp_path / "docs"
    docs.mkdir()
    output = tmp_path / "dossier"
    commands: list[list[str]] = []

    def fake_build_main(arguments: list[str]) -> int:
        assert Path.cwd() == tmp_path
        commands.append(arguments)
        return 0

    monkeypatch.setattr(service, "build_main", fake_build_main)

    result = service.build_dossier(tmp_path, docs=docs, output=output)

    assert result == output / "release-dossier.pdf"
    assert len(commands) == 1
    command = commands[0]
    assert command[command.index("-b") + 1] == "simplepdf"
    assert "pytest" not in command


def test_build_portal_publishes_generated_allure_views(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Portal orchestration composes existing evidence without owning its execution."""
    output = tmp_path / "site"
    output.mkdir()
    (output / "needs.json").write_text("{}", encoding="utf-8")
    raw = tmp_path / "allure-results"
    raw.mkdir()
    calls: list[str] = []

    def fake_build_html(
        root: Path,
        *,
        docs: Path | None = None,
        output: Path | None = None,
    ) -> Path:
        del root, docs, output
        calls.append("html")
        return tmp_path / "site"

    def fake_curate_results(
        raw_results: Path,
        *,
        needs_json: Path,
        curated_results: Path,
        bdd_results: Path,
    ) -> None:
        assert raw_results == raw
        assert needs_json == output / "needs.json"
        curated_results.mkdir(parents=True)
        bdd_results.mkdir(parents=True)
        calls.append("curate")

    def fake_generate_reports(
        *,
        curated_results: Path,
        bdd_results: Path,
        output_root: Path,
    ) -> dict[str, Path]:
        assert curated_results.is_dir()
        assert bdd_results.is_dir()
        calls.append("allure")
        reports: dict[str, Path] = {}
        for name in ("bdd", "requirements", "all"):
            report = output_root / name / "index.html"
            report.parent.mkdir(parents=True)
            report.write_text(name, encoding="utf-8")
            reports[name] = report
        return reports

    monkeypatch.setattr(service, "build_html", fake_build_html)
    monkeypatch.setattr(service, "curate_results", fake_curate_results)
    monkeypatch.setattr(service, "generate_reports", fake_generate_reports)

    result = service.build_portal(tmp_path, allure_results=raw, output=output)

    assert result == output
    assert calls == ["html", "curate", "allure"]
    assert (output / "test-results" / "bdd" / "index.html").read_text() == "bdd"
    assert (output / "test-results" / "requirements" / "index.html").read_text() == (
        "requirements"
    )
    assert (output / "test-results" / "all" / "index.html").read_text() == "all"
    assert (output / "test-results" / "index.html").read_text() == "requirements"
