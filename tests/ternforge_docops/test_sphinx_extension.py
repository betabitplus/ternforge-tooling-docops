"""Hermetic acceptance tests for the shared Sphinx graph profile."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import nbformat
import pytest

from ternforge_docops._internal.experiments.digest import capsule_digest
from ternforge_docops._internal.sphinx import (
    experiments as experiment_sphinx,
    verification,
)


def _run_graph_build(
    tmp_path: Path,
    source: str,
    *,
    evidence: str | None = None,
    warnings_as_errors: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Build one minimal consumer graph and retain native Sphinx diagnostics."""
    docs = tmp_path / "docs"
    output = tmp_path / "html"
    docs.mkdir()
    (docs / "conf.py").write_text(
        'extensions = ["ternforge_docops._api.sphinx"]\nroot_doc = "index"\n',
        encoding="utf-8",
    )
    if evidence is not None:
        (docs / "evidence.xml").write_text(evidence, encoding="utf-8")
    (docs / "index.rst").write_text(source, encoding="utf-8")
    command = [sys.executable, "-m", "sphinx"]
    if warnings_as_errors:
        command.append("-W")
    command.extend(
        [
            "--keep-going",
            "-b",
            "html",
            str(docs),
            str(output),
        ]
    )
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    ("source", "expected_rule"),
    [
        (
            """Missing goal decomposition
==========================

.. goal:: Orphan goal
   :id: GOAL_ORPHAN
""",
            "goal-decomposition",
        ),
        (
            """Missing feature decomposition
=============================

.. goal:: Parent goal
   :id: GOAL_PARENT

.. feature:: Empty feature
   :id: FEAT_EMPTY
   :derives: GOAL_PARENT
""",
            "feature-decomposition",
        ),
    ],
)
def test_graph_schema_rejects_missing_normative_decomposition(
    tmp_path: Path,
    source: str,
    expected_rule: str,
) -> None:
    """Native Sphinx-Needs schema validation owns shallow decomposition laws."""
    result = _run_graph_build(tmp_path, source)

    assert result.returncode != 0
    assert expected_rule in result.stderr
    assert "sn_schema_violation.network_contains_too_few" in result.stderr


@pytest.mark.parametrize("status", ["draft", "deprecated"])
def test_inactive_contract_does_not_require_execution_evidence(
    tmp_path: Path,
    status: str,
) -> None:
    """Keep inactive contract intent without creating release obligations."""
    source = f"""Inactive contract
=================

.. goal:: Parent goal
   :id: GOAL_PARENT

.. feature:: Parent feature
   :id: FEAT_PARENT
   :derives: GOAL_PARENT

.. req:: Inactive requirement
   :id: REQ_INACTIVE
   :status: {status}
   :revision: 1
   :required_evidence: bdd
   :derives: FEAT_PARENT
"""

    result = _run_graph_build(tmp_path, source)

    assert result.returncode == 0
    assert "requested-bdd" not in result.stderr


def test_accepted_contract_still_requires_declared_evidence(tmp_path: Path) -> None:
    """Lifecycle scoping cannot weaken accepted release obligations."""
    source = """Accepted contract
=================

.. goal:: Parent goal
   :id: GOAL_PARENT

.. feature:: Parent feature
   :id: FEAT_PARENT
   :derives: GOAL_PARENT

.. req:: Accepted requirement
   :id: REQ_ACCEPTED
   :status: accepted
   :revision: 1
   :required_evidence: bdd
   :derives: FEAT_PARENT
"""

    result = _run_graph_build(tmp_path, source)

    assert result.returncode != 0
    assert "requested-bdd" in result.stderr
    assert "sn_schema_violation.network_contains_too_few" in result.stderr


def test_sphinx_extension_builds_current_graph(tmp_path: Path) -> None:
    """A consumer builds requirements without copying the graph ontology."""
    docs = tmp_path / "docs"
    output = tmp_path / "html"
    docs.mkdir()
    (docs / "conf.py").write_text(
        'extensions = ["ternforge_docops._api.sphinx"]\nroot_doc = "index"\n',
        encoding="utf-8",
    )
    (docs / "evidence.xml").write_text(
        """<testsuites>
<testsuite name="docops">
<testcase classname="tests.test_docops" name="test_shared_requirement">
<properties>
<property name="verification_kind" value="integration"/>
<property name="verifies" value="REQ_DOCOPS[revision==1]"/>
</properties>
</testcase>
</testsuite>
</testsuites>
""",
        encoding="utf-8",
    )
    (docs / "index.rst").write_text(
        """DocOps graph acceptance
=======================

.. goal:: Shared graph
   :id: GOAL_DOCOPS

.. feature:: Shared feature
   :id: FEAT_DOCOPS
   :derives: GOAL_DOCOPS

.. req:: Shared requirement
   :id: REQ_DOCOPS
   :status: accepted
   :revision: 1
   :required_evidence: integration
   :derives: FEAT_DOCOPS

.. test-file:: Shared execution evidence
   :id: TEST_DOCOPS
   :file: evidence.xml
   :auto_suites:
   :auto_cases:

Verification matrix
-------------------

.. ternforge-verification-matrix::

Specification health
--------------------

.. ternforge-specification-health::
""",
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            "-m",
            "sphinx",
            "-W",
            "--keep-going",
            "-b",
            "html",
            str(docs),
            str(output),
        ],
        check=True,
    )

    index = (output / "index.html").read_text(encoding="utf-8")
    assert (output / "needs.json").is_file()
    assert "Product requirements" in index
    assert "REQ_DOCOPS" in index
    assert "✓ 1/1" in index
    assert "Coverage summary" in index
    assert "Goals" in index
    assert "Accepted requirements" in index
    assert "No active specification coverage gaps." in index
    assert "MISSING" not in index
    assert "_static/ternforge-docops.css" in index
    assert (output / "_static" / "ternforge-docops.css").is_file()
    assert "_static/ternforge-data-viewer.js" not in index
    assert "_static/ternforge-docops.js" not in index


@pytest.mark.parametrize(
    ("pinned_revision", "expected_status"),
    [(1, "OUTDATED 1"), (3, "PREDATED 1")],
)
def test_verification_matrix_surfaces_noncurrent_revision_evidence(
    tmp_path: Path,
    pinned_revision: int,
    expected_status: str,
) -> None:
    """Resolved Needs keep stale backlinks, but the matrix never calls them current."""
    source = """Revision-aware matrix
=====================

.. goal:: Shared graph
   :id: GOAL_DOCOPS

.. feature:: Shared feature
   :id: FEAT_DOCOPS
   :derives: GOAL_DOCOPS

.. req:: Shared requirement
   :id: REQ_DOCOPS
   :status: accepted
   :revision: 2
   :required_evidence: integration
   :derives: FEAT_DOCOPS

.. test-file:: Shared execution evidence
   :id: TEST_DOCOPS
   :file: evidence.xml
   :auto_suites:
   :auto_cases:

Verification matrix
-------------------

.. ternforge-verification-matrix::
"""
    evidence = f"""<testsuites>
<testsuite name="docops">
<testcase classname="tests.test_docops" name="test_shared_requirement">
<properties>
<property name="verification_kind" value="integration"/>
<property name="verifies" value="REQ_DOCOPS[revision=={pinned_revision}]"/>
</properties>
</testcase>
</testsuite>
</testsuites>
"""

    result = _run_graph_build(
        tmp_path,
        source,
        evidence=evidence,
        warnings_as_errors=False,
    )

    assert result.returncode == 0
    assert "needs.link_condition_failed" in result.stderr
    index = (tmp_path / "html" / "index.html").read_text(encoding="utf-8")
    assert expected_status in index
    assert "✓ 1/1" not in index


def test_verification_counts_respect_revision_pins() -> None:
    """Verification presentation never treats stale conditional links as current."""
    needs = [
        {
            "id": "REQ_DEMO",
            "type": "req",
            "revision": 2,
            "required_evidence": ["integration"],
        },
        {
            "id": "TEST_CURRENT",
            "type": "testcase",
            "result": "passed",
            "verification_kind": "integration",
            "verifies": ["REQ_DEMO[revision==2]"],
        },
        {
            "id": "TEST_OUTDATED",
            "type": "testcase",
            "result": "passed",
            "verification_kind": "integration",
            "verifies": ["REQ_DEMO[revision==1]"],
        },
        {
            "id": "TEST_PREDATED",
            "type": "testcase",
            "result": "passed",
            "verification_kind": "integration",
            "verifies": ["REQ_DEMO[revision==3]"],
        },
        {
            "id": "TEST_UNPINNED",
            "type": "testcase",
            "result": "passed",
            "verification_kind": "integration",
            "verifies": ["REQ_DEMO"],
        },
    ]

    counts = verification._verification_counts_from_needs(needs)

    assert counts["REQ_DEMO"]["integration"] == (1, 1, 1, 1)
    assert (
        verification._status_text(counts["REQ_DEMO"]["integration"], required=True)
        == "✓ 1/1 · OUTDATED 1 · PREDATED 1"
    )


def test_stale_verification_without_current_evidence_is_not_green() -> None:
    """A stale passed testcase is visible but cannot satisfy current evidence."""
    needs = [
        {"id": "REQ_DEMO", "type": "req", "revision": 2},
        {
            "id": "TEST_OUTDATED",
            "type": "testcase",
            "result": "passed",
            "verification_kind": "bdd",
            "verifies": ["REQ_DEMO[revision==1]"],
        },
    ]

    counts = verification._verification_counts_from_needs(needs)

    assert counts["REQ_DEMO"]["bdd"] == (0, 0, 1, 0)
    assert verification._status_text(counts["REQ_DEMO"]["bdd"], required=True) == (
        "OUTDATED 1"
    )


def test_contract_provenance_follows_declared_graph_relations() -> None:
    """Contract provenance exposes only relations already present in the Needs graph."""
    needs = {
        "REQ_DEMO": {
            "id": "REQ_DEMO",
            "type": "req",
            "derives_back": ["TREQ_DEMO"],
            "affects_back": ["ADR_DEMO"],
            "implements_back": ["IMPL_REQ"],
        },
        "TREQ_DEMO": {
            "id": "TREQ_DEMO",
            "type": "treq",
            "affects_back": ["ADR_DEMO"],
            "informs_back": ["EXP_DEMO"],
            "implements_back": ["IMPL_TREQ"],
        },
        "ADR_DEMO": {
            "id": "ADR_DEMO",
            "type": "adr",
            "informs_back": ["EXP_DEMO"],
        },
        "EXP_DEMO": {"id": "EXP_DEMO", "type": "exp"},
        "IMPL_REQ": {"id": "IMPL_REQ", "type": "impl"},
        "IMPL_TREQ": {"id": "IMPL_TREQ", "type": "impl"},
    }

    assert verification._provenance_groups(needs, ("REQ_DEMO",)) == (
        ("Verified contract", ("REQ_DEMO",)),
        ("Engineering constraints", ("TREQ_DEMO",)),
        ("Architecture decisions", ("ADR_DEMO",)),
        ("Research evidence", ("EXP_DEMO",)),
        ("Implementation loci", ("IMPL_REQ", "IMPL_TREQ")),
    )


def test_experiment_run_details_are_collapsed_and_surface_stale_state(
    tmp_path: Path,
) -> None:
    """Standard Jupyter timing stays quiet unless Ternforge freshness is stale."""
    capsule = tmp_path / "exp_0001_demo"
    capsule.mkdir()
    notebook = nbformat.v4.new_notebook(
        cells=[
            nbformat.v4.new_markdown_cell("# Demo"),
            nbformat.v4.new_code_cell(
                "setup = True",
                execution_count=1,
                metadata={
                    "tags": ["exp-setup"],
                    "execution": {
                        "iopub.status.busy": "2026-09-10T08:00:00Z",
                        "iopub.status.idle": "2026-09-10T08:00:01Z",
                    },
                },
            ),
            nbformat.v4.new_markdown_cell(
                "## 1. Probe capability",
                metadata={"tags": ["exp-step"]},
            ),
            nbformat.v4.new_code_cell(
                "print('ok')",
                execution_count=2,
                metadata={
                    "tags": ["exp-evidence"],
                    "execution": {
                        "iopub.status.busy": "2026-09-10T08:00:01Z",
                        "iopub.status.idle": "2026-09-10T08:00:03Z",
                    },
                },
            ),
        ],
        metadata={
            "kernelspec": {
                "display_name": "Python 3.13.7",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.13.7"},
            "ternforge": {"capsule_digest": "UNSET"},
        },
    )
    notebook.metadata["ternforge"]["capsule_digest"] = capsule_digest(capsule, notebook)

    current = experiment_sphinx._run_details(capsule, notebook)

    assert current.startswith(":::{dropdown} Run details")
    assert "**Captured:** 2026-09-10 08:00 UTC" in current
    assert "**Capture duration:** 3.0 s" in current
    assert "**Runtime:** Python 3.13.7 (`python3`)" in current
    assert "**Freshness:** Current" in current
    assert "| 1. Probe capability | 2.0 s |" in current
    assert "{warning}" not in current

    inputs = capsule / "inputs"
    inputs.mkdir()
    (inputs / "new-causal-input.txt").write_text("changed\n", encoding="utf-8")
    stale = experiment_sphinx._run_details(capsule, notebook)

    assert stale.startswith(":::{warning}")
    assert "**Captured evidence is stale.**" in stale
    assert "**Freshness:** Stale" in stale


def test_sphinx_extension_mounts_experiment_reports_in_place(tmp_path: Path) -> None:
    """Captured notebooks stay in capsules while Sphinx sees stable docnames."""
    docs = tmp_path / "docs"
    output = tmp_path / "html"
    docs.mkdir()
    (docs / "conf.py").write_text(
        'extensions = ["ternforge_docops._api.sphinx"]\nroot_doc = "index"\n',
        encoding="utf-8",
    )
    (docs / "index.rst").write_text(
        """Experiment mount acceptance
===========================

.. toctree::
   :maxdepth: 1

   experiments/_generated/exp_0001_demo/report
""",
        encoding="utf-8",
    )

    capsule = tmp_path / "experiments" / "sample" / "exp_0001_demo"
    report_dir = capsule / "report"
    inputs = capsule / "inputs"
    report_dir.mkdir(parents=True)
    inputs.mkdir()
    (inputs / "probe.txt").write_text("mounted evidence", encoding="utf-8")
    notebook = nbformat.v4.new_notebook(
        cells=[
            nbformat.v4.new_markdown_cell(
                """# Mounted experiment

```{exp} Demo experiment
:id: EXP_0001
:experiment_date: 2026-09-02
```
"""
            ),
            nbformat.v4.new_code_cell(
                "pass",
                execution_count=1,
                metadata={
                    "execution": {
                        "iopub.status.busy": "2026-09-10T08:00:00Z",
                        "iopub.status.idle": "2026-09-10T08:00:02Z",
                    }
                },
                outputs=[
                    nbformat.v4.new_output(
                        "display_data",
                        data={
                            "image/png": (
                                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lE"
                                "QVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
                            ),
                            "text/html": '<a href="inputs/probe.txt">probe</a>',
                            "text/plain": "probe",
                        },
                    )
                ],
            ),
        ],
        metadata={
            "kernelspec": {
                "display_name": "Python 3.13.7",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.13.7"},
            "ternforge": {"capsule_digest": "UNSET"},
        },
    )
    notebook.metadata["ternforge"]["capsule_digest"] = capsule_digest(capsule, notebook)
    retained_source = str(notebook.cells[0].source)
    nbformat.write(notebook, report_dir / "report.ipynb")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "sphinx",
            "-W",
            "--keep-going",
            "-b",
            "html",
            str(docs),
            str(output),
        ],
        check=True,
    )

    mounted_report = (
        output / "experiments" / "_generated" / "exp_0001_demo" / "report.html"
    )
    published_input = (
        output / "experiments" / "_generated" / "exp_0001_demo" / "inputs" / "probe.txt"
    )
    assert mounted_report.is_file()
    mounted_html = mounted_report.read_text(encoding="utf-8")
    assert "Mounted experiment" in mounted_html
    assert "EXP_0001" in mounted_html
    assert "experiment_date" in mounted_html
    assert "2026-09-02" in mounted_html
    assert "Run details" in mounted_html
    assert "2026-09-10 08:00 UTC" in mounted_html
    assert "2.0 s" in mounted_html
    assert "Python 3.13.7" in mounted_html
    assert "Freshness:" in mounted_html
    assert "Current" in mounted_html
    assert "<details" in mounted_html
    assert published_input.read_text(encoding="utf-8") == "mounted evidence"
    retained = nbformat.read(report_dir / "report.ipynb", as_version=4)
    assert str(retained.cells[0].source) == retained_source
    assert "Run details" not in str(retained.cells[0].source)
    assert not (docs / "experiments" / "_generated").exists()
