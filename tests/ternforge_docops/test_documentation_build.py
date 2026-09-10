"""Tests for documentation presentation orchestration."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

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
    assert "plot_gallery=0" in command
    assert "pytest" not in command


def test_build_html_can_execute_live_gallery_examples(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Trusted publication can opt into Sphinx-Gallery execution explicitly."""
    docs = tmp_path / "docs"
    docs.mkdir()
    commands: list[list[str]] = []
    monkeypatch.setattr(
        service, "build_main", lambda arguments: commands.append(arguments) or 0
    )

    service.build_html(tmp_path, docs=docs, live_examples=True)

    assert len(commands) == 1
    assert "plot_gallery=0" not in commands[0]


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
    assert "plot_gallery=0" in command
    assert "llms_txt_enabled=0" in command
    assert "pytest" not in command


def test_build_dossier_materializes_living_specs_from_allure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The PDF dossier sees the same Living Specs evidence as the HTML portal."""
    docs = tmp_path / "docs"
    docs.mkdir()
    output = tmp_path / "dossier"
    raw = tmp_path / "allure-results"
    raw.mkdir()
    calls: list[str] = []

    def fake_curate_results(
        raw_results: Path,
        *,
        curated_results: Path,
    ) -> None:
        assert raw_results == raw
        curated_results.mkdir(parents=True)
        calls.append("curate")

    def fake_generate_report(
        *,
        curated_results: Path,
        output: Path,
    ) -> Path:
        assert curated_results.is_dir()
        calls.append("allure")
        report = output / "index.html"
        report.parent.mkdir(parents=True)
        report.write_text("all", encoding="utf-8")
        return report

    monkeypatch.setattr(
        service,
        "render_living_specifications",
        lambda root, raw_results, *, result_links: SimpleNamespace(
            source="Current executable behavior\n",
            assets=(),
            pages=(
                SimpleNamespace(
                    docname="specifications/_generated/routing/fallback",
                    source="Route fallback\n==============\n",
                ),
            ),
        ),
    )

    def fake_run_sphinx(
        root: Path,
        docs_root: Path,
        output_root: Path,
        builder: str,
        *,
        live_examples: bool = False,
    ) -> None:
        assert root == tmp_path
        assert docs_root == docs
        assert output_root == output
        assert builder == "simplepdf"
        assert live_examples is False
        assert (
            "Current executable behavior"
            in (docs_root / service._LIVING_SOURCE).read_text()
        )
        feature_page = (
            docs_root / "specifications" / "_generated" / "routing" / "fallback.rst"
        )
        assert feature_page.is_file()
        calls.append("simplepdf")

    monkeypatch.setattr(service, "curate_results", fake_curate_results)
    monkeypatch.setattr(service, "generate_report", fake_generate_report)
    monkeypatch.setattr(service, "_run_sphinx", fake_run_sphinx)

    result = service.build_dossier(
        tmp_path,
        docs=docs,
        output=output,
        allure_results=raw,
    )

    assert result == output / "release-dossier.pdf"
    assert calls == ["curate", "allure", "simplepdf"]
    assert not (docs / "specifications" / "_generated").exists()


def test_build_portal_publishes_living_specs_and_allure_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Portal composes native Living Specs and keeps Allure diagnostics in parallel."""
    output = tmp_path / "site"
    output.mkdir()
    (output / "needs.json").write_text("{}", encoding="utf-8")
    raw = tmp_path / "allure-results"
    raw.mkdir()
    calls: list[str] = []

    def fake_run_sphinx(
        root: Path,
        docs_root: Path,
        output_root: Path,
        builder: str,
        *,
        live_examples: bool = False,
    ) -> None:
        assert root == tmp_path
        assert docs_root == tmp_path / "docs"
        assert output_root == output
        assert builder == "html"
        assert live_examples is False
        living = docs_root / service._LIVING_SOURCE
        assert living.is_file()
        assert "Generated by Ternforge DocOps" in living.read_text()
        assert "Current executable behavior" in living.read_text()
        assert (docs_root / "specifications.rst").is_file()
        feature_page = (
            docs_root / "specifications" / "_generated" / "routing" / "fallback.rst"
        )
        assert feature_page.is_file()
        assert "Generated by Ternforge DocOps" in feature_page.read_text()
        assert "Route fallback" in feature_page.read_text()
        (output_root / "needs.json").write_text("{}", encoding="utf-8")
        calls.append("html")

    def fake_curate_results(
        raw_results: Path,
        *,
        curated_results: Path,
    ) -> None:
        assert raw_results == raw
        curated_results.mkdir(parents=True)
        calls.append("curate")

    def fake_generate_report(
        *,
        curated_results: Path,
        output: Path,
    ) -> Path:
        assert curated_results.is_dir()
        calls.append("allure")
        report = output / "index.html"
        report.parent.mkdir(parents=True)
        report.write_text("all", encoding="utf-8")
        return report

    monkeypatch.setattr(
        service,
        "render_living_specifications",
        lambda root, raw_results, *, result_links: SimpleNamespace(
            source="Current executable behavior\n",
            assets=(),
            pages=(
                SimpleNamespace(
                    docname="specifications/_generated/routing/fallback",
                    source="Route fallback\n==============\n",
                ),
            ),
        ),
    )
    monkeypatch.setattr(service, "publish_living_assets", lambda report, target: None)
    monkeypatch.setattr(service, "_run_sphinx", fake_run_sphinx)
    monkeypatch.setattr(service, "curate_results", fake_curate_results)
    monkeypatch.setattr(service, "generate_report", fake_generate_report)

    result = service.build_portal(tmp_path, allure_results=raw, output=output)

    assert result == output
    assert calls == ["curate", "allure", "html"]
    assert not (tmp_path / "docs" / "specifications" / "_generated").exists()
    assert (output / "test-results" / "index.html").read_text() == "all"
    assert not (output / "test-results" / "bdd").exists()
    assert not (output / "test-results" / "requirements").exists()
    assert not (output / "test-results" / "all").exists()


def test_build_materializes_shared_views_and_junit_only_for_build(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Generic views and JUnit ingestion are owned and cleaned up by DocOps."""
    docs = tmp_path / "docs"
    docs.mkdir()
    junit = tmp_path / "pytest-junit.xml"
    junit.write_text("<testsuites/>", encoding="utf-8")

    def fake_build_main(arguments: list[str]) -> int:
        del arguments
        assert (docs / "traceability.rst").is_file()
        assert (docs / "verification.rst").is_file()
        assert (docs / "specification-health.rst").is_file()
        assert (docs / "tests.rst").is_file()
        evidence = docs / "ternforge-test-evidence.rst"
        imported = docs / "_traceability" / "ternforge-test-evidence.xml"
        assert ".. test-file:: Imported test evidence" in evidence.read_text()
        assert imported.read_text() == "<testsuites/>"
        return 0

    monkeypatch.setattr(service, "build_main", fake_build_main)

    service.build_html(tmp_path, docs=docs, junit=junit)

    assert not (docs / "traceability.rst").exists()
    assert not (docs / "verification.rst").exists()
    assert not (docs / "specification-health.rst").exists()
    assert not (docs / "tests.rst").exists()
    assert not (docs / "ternforge-test-evidence.rst").exists()
    assert not (docs / "_traceability" / "ternforge-test-evidence.xml").exists()


def test_build_preserves_consumer_override_of_shared_view(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A project-specific page may override a package-owned default."""
    docs = tmp_path / "docs"
    docs.mkdir()
    override = docs / "traceability.rst"
    override.write_text("project-specific", encoding="utf-8")
    monkeypatch.setattr(service, "build_main", lambda arguments: 0)

    service.build_html(tmp_path, docs=docs)

    assert override.read_text() == "project-specific"


def test_build_recovers_transient_sources_left_by_interrupted_build(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A later build adopts and cleans exact DocOps transient materialization."""
    docs = tmp_path / "docs"
    docs.mkdir()
    shared = service.shared_docs_dir_path()
    for name in (
        "traceability.rst",
        "verification.rst",
        "specification-health.rst",
        "tests.rst",
    ):
        (docs / name).write_bytes((shared / name).read_bytes())

    trace_dir = docs / "_traceability"
    trace_dir.mkdir()
    (docs / "ternforge-test-evidence.rst").write_text(
        service._EVIDENCE_SOURCE_TEXT,
        encoding="utf-8",
    )
    (trace_dir / "ternforge-test-evidence.xml").write_text(
        "<testsuites stale='true'/>",
        encoding="utf-8",
    )
    junit = tmp_path / "pytest-junit.xml"
    junit.write_text("<testsuites fresh='true'/>", encoding="utf-8")

    def fake_build_main(arguments: list[str]) -> int:
        del arguments
        imported = trace_dir / "ternforge-test-evidence.xml"
        assert imported.read_text() == "<testsuites fresh='true'/>"
        return 0

    monkeypatch.setattr(service, "build_main", fake_build_main)

    service.build_html(tmp_path, docs=docs, junit=junit)

    for name in (
        "traceability.rst",
        "verification.rst",
        "specification-health.rst",
        "tests.rst",
    ):
        assert not (docs / name).exists()
    assert not (docs / "ternforge-test-evidence.rst").exists()
    assert not (trace_dir / "ternforge-test-evidence.xml").exists()


def test_build_without_junit_discards_stale_reserved_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Offline builds cannot accidentally import JUnit left by an interrupted run."""
    docs = tmp_path / "docs"
    trace_dir = docs / "_traceability"
    trace_dir.mkdir(parents=True)
    (docs / "ternforge-test-evidence.rst").write_text(
        service._EVIDENCE_SOURCE_TEXT,
        encoding="utf-8",
    )
    (trace_dir / "ternforge-test-evidence.xml").write_text(
        "<testsuites stale='true'/>",
        encoding="utf-8",
    )

    def fake_build_main(arguments: list[str]) -> int:
        del arguments
        assert not (docs / "ternforge-test-evidence.rst").exists()
        assert not (trace_dir / "ternforge-test-evidence.xml").exists()
        return 0

    monkeypatch.setattr(service, "build_main", fake_build_main)

    service.build_html(tmp_path, docs=docs)

    assert not trace_dir.exists()
