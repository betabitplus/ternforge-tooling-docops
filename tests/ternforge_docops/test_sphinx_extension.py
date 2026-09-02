"""Hermetic acceptance tests for the shared Sphinx graph profile."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import nbformat


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
            nbformat.v4.new_markdown_cell("# Mounted experiment"),
            nbformat.v4.new_code_cell(
                "pass",
                execution_count=1,
                outputs=[
                    nbformat.v4.new_output(
                        "display_data",
                        data={
                            "text/html": '<a href="inputs/probe.txt">probe</a>',
                            "text/plain": "probe",
                        },
                    )
                ],
            ),
        ],
        metadata={
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            }
        },
    )
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
    assert "Mounted experiment" in mounted_report.read_text(encoding="utf-8")
    assert published_input.read_text(encoding="utf-8") == "mounted evidence"
    assert not (docs / "experiments" / "_generated").exists()
