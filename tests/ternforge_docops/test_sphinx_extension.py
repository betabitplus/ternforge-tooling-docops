"""Hermetic acceptance tests for the shared Sphinx graph profile."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import nbformat

from ternforge_docops._internal.experiments.digest import capsule_digest
from ternforge_docops._internal.sphinx import (
    experiments as experiment_sphinx,
    verification,
)


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
    assert "MISSING" not in index
    assert "_static/ternforge-docops.css" in index
    assert (output / "_static" / "ternforge-docops.css").is_file()
    assert "_static/ternforge-data-viewer.js" not in index
    assert "_static/ternforge-docops.js" not in index


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
