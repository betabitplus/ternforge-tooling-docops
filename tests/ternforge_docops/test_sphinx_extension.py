"""Hermetic acceptance tests for the shared Sphinx graph profile."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import nbformat
import pytest

from ternforge_docops._internal.experiments.digest import capsule_digest
from ternforge_docops._internal.resources import shared_docs_dir_path
from ternforge_docops._internal.sphinx import (
    experiments as experiment_sphinx,
    verification,
)
from ternforge_docops._internal.sphinx.review_common import bdd_scenario_url


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


def test_shared_pydata_theme_defaults_to_auto_mode(tmp_path: Path) -> None:
    """A fresh browser must not start with an invalid empty PyData theme mode."""
    result = _run_graph_build(tmp_path, "Portal\n======\n")

    assert result.returncode == 0
    html = (tmp_path / "html" / "index.html").read_text(encoding="utf-8")
    assert 'localStorage.getItem("mode") || "auto"' in html
    assert 'localStorage.getItem("theme") || "auto"' in html


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


def test_supplemental_verification_evidence_is_allowed(tmp_path: Path) -> None:
    """Required evidence is a minimum contract, not a verification-kind whitelist."""
    source = """Supplemental verification
==========================

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

.. test-file:: Execution evidence
   :id: TEST_FILE
   :file: evidence.xml
   :auto_suites:
   :auto_cases:
"""
    evidence = """<testsuites>
<testsuite name="supplemental">
<testcase classname="tests.test_demo" name="test_required_bdd">
<properties>
<property name="verification_kind" value="bdd"/>
<property name="verifies" value="REQ_ACCEPTED[revision==1]"/>
</properties>
</testcase>
<testcase classname="tests.test_demo" name="test_supplemental_unit">
<properties>
<property name="verification_kind" value="unit"/>
<property name="verifies" value="REQ_ACCEPTED[revision==1]"/>
</properties>
</testcase>
</testsuite>
</testsuites>
"""

    result = _run_graph_build(tmp_path, source, evidence=evidence)

    assert result.returncode == 0
    assert "requested-bdd" not in result.stderr
    assert "unwanted-unit" not in result.stderr


def test_impl_only_assurance_has_no_false_live_reality_gap(
    tmp_path: Path,
) -> None:
    """Implementation-only proof must not imply a missing live execution."""
    source = """Implementation-only assurance
=============================

.. goal:: Parent goal
   :id: GOAL_IMPL_ONLY

.. feature:: Parent capability
   :id: FEAT_IMPL_ONLY
   :derives: GOAL_IMPL_ONLY

.. req:: Implementation-only contract
   :id: REQ_IMPL_ONLY
   :status: accepted
   :revision: 1
   :required_evidence: impl
   :derives: FEAT_IMPL_ONLY

.. impl:: Implementation
   :id: IMPL_ONLY
   :implements: REQ_IMPL_ONLY[revision==1]
   :source_url: https://example.invalid/src/impl.py

.. ternforge-verification-assurance-map::
"""

    result = _run_graph_build(tmp_path, source)

    assert result.returncode == 0, result.stderr
    html = (tmp_path / "html" / "index.html").read_text(encoding="utf-8")
    assert "No execution evidence is retained for current proof." in html
    assert "Live reality gap:" not in html


def test_shared_evidence_trust_registry_builds(tmp_path: Path) -> None:
    """The package-owned generic producer registry is a valid strict Needs graph."""
    source = (shared_docs_dir_path() / "evidence-trust.rst").read_text(encoding="utf-8")

    result = _run_graph_build(tmp_path, source)

    assert result.returncode == 0, result.stderr
    html = (tmp_path / "html" / "index.html").read_text(encoding="utf-8")
    assert "Ternforge py-testkit evidence transport" in html
    assert "Scripted HTTP server" in html
    assert "not calibrated against live external reality" in html
    assert "Revision pin graph cross-check" in html


def test_complementary_evidence_context_links_same_claim_scope(
    tmp_path: Path,
) -> None:
    """Narratives expose nearby current proof and an explicit remaining reach gap."""
    source = """Complementary evidence
======================

.. goal:: Parent goal
   :id: GOAL_PARENT

.. feature:: Parent capability
   :id: FEAT_PARENT
   :derives: GOAL_PARENT

.. req:: Shared claim
   :id: REQ_SHARED
   :status: accepted
   :revision: 1
   :required_evidence: unit
   :derives: FEAT_PARENT

.. test-file:: Execution evidence
   :id: TEST_FILE
   :file: evidence.xml
   :auto_suites:
   :auto_cases:

.. ternforge-evidence-context:: REQ_SHARED
   :current-nodeids: tests/test_shared.py::test_focused
"""
    evidence = """<testsuites>
<testsuite name="scope">
<testcase classname="tests.test_shared" name="test_focused">
<properties>
<property name="verification_kind" value="unit"/>
<property name="verifies" value="REQ_SHARED[revision==1]"/>
<property name="nodeid" value="tests/test_shared.py::test_focused"/>
<property name="scope_reach" value="focused_logic"/>
<property name="scope_basis" value="captured production coverage"/>
<property name="external_reach" value="local"/>
</properties>
</testcase>
<testcase classname="tests.test_shared" name="test_boundary">
<properties>
<property name="verification_kind" value="integration"/>
<property name="verifies" value="REQ_SHARED[revision==1]"/>
<property name="nodeid" value="tests/test_shared.py::test_boundary"/>
<property name="scope_reach" value="transport_sdk_filesystem"/>
<property name="scope_basis" value="captured boundary interaction"/>
<property name="external_reach" value="substitute"/>
</properties>
</testcase>
</testsuite>
</testsuites>
"""

    result = _run_graph_build(tmp_path, source, evidence=evidence)

    assert result.returncode == 0, result.stderr
    html = (tmp_path / "html" / "index.html").read_text(encoding="utf-8")
    assert "Covered elsewhere:" in html
    assert "Boundary (Transport / SDK / filesystem)" in html
    assert "Remaining gap:" in html
    assert "no direct live external interaction is retained" in html


def test_evidence_producer_graph_accepts_trust_and_calibration_links(
    tmp_path: Path,
) -> None:
    """Keep producer trust graph-native and link testcase evidence to its producer."""
    source = """Evidence producer assurance
===========================

.. goal:: Parent goal
   :id: GOAL_PARENT

.. feature:: Parent capability
   :id: FEAT_PARENT
   :derives: GOAL_PARENT

.. req:: Provider behavior
   :id: REQ_PROVIDER
   :status: accepted
   :revision: 1
   :required_evidence: integration
   :derives: FEAT_PARENT

.. qualification:: HTTP helper contract tests
   :id: QUAL_HTTP_UNIT
   :qualification_kind: unit-contract
   :target_version: py-lib-testkit-v1
   :evidence_url: https://example.invalid/http-unit

.. qualification:: HTTP helper integration tests
   :id: QUAL_HTTP_INTEGRATION
   :qualification_kind: integration-contract
   :target_version: py-lib-testkit-v1
   :evidence_url: https://example.invalid/http-integration

.. producer:: Scripted provider HTTP
   :id: PRODUCER_SCRIPTED_HTTP
   :producer_role: test-substitute
   :producer_version: py-lib-testkit-v1
   :producer_impact: high
   :producer_purpose: Emit deterministic provider-shaped HTTP behavior.
   :risk_if_wrong: Integration evidence can overstate provider behavior.
   :residual_doubt: A live provider may change after calibration.
   :qualified_by: QUAL_HTTP_UNIT;QUAL_HTTP_INTEGRATION

.. manual:: Live HTTP comparison
   :id: MANUAL_HTTP_CALIBRATION
   :manual_date: 2026-09-12
   :target_version: provider-current
   :performed_by: controlled procedure
   :artifact_url: https://example.invalid/http-live
   :manual_scope: provider HTTP response and retry shape
   :limitation: one provider path and captured provider revision
   :calibrates: PRODUCER_SCRIPTED_HTTP

.. test-file:: Execution evidence
   :id: TEST_FILE
   :file: evidence.xml
   :auto_suites:
   :auto_cases:

.. ternforge-evidence-context:: REQ_PROVIDER
   :current-nodeids: tests/test_provider.py::test_provider

.. ternforge-verification-assurance-map::

.. ternforge-evidence-trust::
"""
    evidence = """<testsuites>
<testsuite name="producer">
<testcase classname="tests.test_provider" name="test_provider">
<properties>
<property name="verification_kind" value="integration"/>
<property name="verifies" value="REQ_PROVIDER[revision==1]"/>
<property name="produced_by" value="PRODUCER_SCRIPTED_HTTP"/>
<property name="nodeid" value="tests/test_provider.py::test_provider"/>
<property name="scope_reach" value="transport_sdk_filesystem"/>
<property name="scope_basis" value="captured boundary interaction"/>
<property name="external_reach" value="substitute"/>
</properties>
</testcase>
</testsuite>
</testsuites>
"""

    result = _run_graph_build(tmp_path, source, evidence=evidence)

    assert result.returncode == 0, result.stderr
    needs = (tmp_path / "html" / "needs.json").read_text(encoding="utf-8")
    assert "PRODUCER_SCRIPTED_HTTP" in needs
    assert "transport_sdk_filesystem" in needs
    assert "QUAL_HTTP_INTEGRATION" in needs
    assert "MANUAL_HTTP_CALIBRATION" in needs
    html = (tmp_path / "html" / "index.html").read_text(encoding="utf-8")
    assert "Verification scope:" in html
    assert "Transport / SDK / filesystem" in html
    assert "Live reality gap:" in html
    assert "Trust of evidence:" in html
    assert "Evidence producers:" in html
    assert 'href="evidence-trust.html#evidence-trust-producer-scripted-http"' in html
    assert "Trust state:" in html
    assert "multiple trust-basis records satisfy high-impact policy" in html
    assert "Trust basis" in html
    assert "calibration evidence linked" in html


def test_high_impact_producer_requires_stronger_trust_basis(tmp_path: Path) -> None:
    """One trust record cannot silently qualify a high-impact producer."""
    source = """Producer trust gap
==================

.. qualification:: One check
   :id: QUAL_ONE
   :qualification_kind: unit-contract
   :target_version: helper-v1
   :evidence_url: https://example.invalid/one

.. producer:: High impact helper
   :id: PRODUCER_HIGH
   :producer_role: evidence-transformer
   :producer_version: helper-v1
   :producer_impact: high
   :producer_purpose: Select evidence.
   :risk_if_wrong: False confidence.
   :residual_doubt: Integration behavior remains independent.
   :qualified_by: QUAL_ONE
"""

    result = _run_graph_build(tmp_path, source)

    assert result.returncode != 0
    assert "high-impact-producer-trust" in result.stderr


def test_manual_verification_requires_retained_calibration_metadata(
    tmp_path: Path,
) -> None:
    """Manual calibration cannot exist without date/version/artifact/scope/limit."""
    source = """Manual calibration
==================

.. manual:: Incomplete live comparison
   :id: MANUAL_PROVIDER
   :manual_date: 2026-09-12
   :target_version: provider-current
   :performed_by: operator
   :manual_scope: response shape
   :limitation: one provider path only
"""

    result = _run_graph_build(tmp_path, source)

    assert result.returncode != 0
    assert "manual-verification-contract" in result.stderr


def test_sphinx_extension_builds_current_graph(tmp_path: Path) -> None:  # noqa: PLR0915
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

   Keep shared engineering intent readable end to end.

.. feature:: Shared feature
   :id: FEAT_DOCOPS
   :derives: GOAL_DOCOPS

   Preserve a human-readable capability branch.

.. req:: Shared requirement
   :id: REQ_DOCOPS
   :status: accepted
   :revision: 1
   :required_evidence: impl;integration
   :derives: FEAT_DOCOPS

   **Statement.** Shared behavior shall remain reviewable.

   **Rationale.** Human reviewers need useful prose before technical identity.

   **Verification intent.** Verify the shared behavior through integration evidence.

.. impl:: Shared implementation
   :id: IMPL_DOCOPS
   :implements: REQ_DOCOPS[revision==1]
   :source_url: https://example.invalid/src/shared.py

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

Traceability reader
-------------------

.. ternforge-traceability-reader::

Verification assurance
----------------------

.. ternforge-verification-assurance-map::

Specification map
-----------------

.. ternforge-specification-map::
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
    assert "Requirements" in index
    assert "REQ_DOCOPS" in index
    assert "✓ 1/1" in index
    assert "What needs attention" in index
    assert "No active specification coverage gaps." in index
    assert "Audit totals" in index
    assert index.index("What needs attention") < index.index("Audit totals")
    assert "Goals" in index
    assert "Capabilities" in index
    assert "MISSING" not in index
    assert "_static/ternforge-docops.css" in index
    assert (output / "_static" / "ternforge-docops.css").is_file()
    assert "_static/ternforge-data-viewer.js" not in index
    assert "_static/ternforge-docops.js" not in index
    assert "_static/ternforge-traceability-canvas.js" not in index
    assert not (output / "_static" / "ternforge-traceability-canvas.js").exists()
    assert all(
        marker in index
        for marker in (
            "ternforge-review-layout",
            "ternforge-review-navigation",
            "Goals &amp; capabilities",
            'href="#review-GOAL_DOCOPS"',
            'href="#review-FEAT_DOCOPS"',
        )
    )
    assert "ternforge-review-jumps" not in index
    assert "ternforge-traceability-reader" in index
    assert "ternforge-hierarchy-card" in index
    assert "ternforge-requirement-flow" in index
    assert "Why this exists" in index
    assert "What must be true" in index
    assert "What proves it now" in index
    assert '<span class="ternforge-trace-number">1</span>' in index
    assert '<span class="ternforge-trace-number">1.1</span>' in index
    assert '<span class="ternforge-trace-number">1.1.1</span>' in index
    assert "Goal" in index
    assert "Preserve a human-readable capability branch." in index
    assert "Shared behavior shall remain reviewable." in index
    assert "Human reviewers need useful prose before technical identity." in index
    assert "Current proof is complete" in index
    assert "Integration verification" in index
    assert ">1 check</summary>" in index
    assert "IDs and revision" in index
    assert "Verification assurance" in index
    assert "Current proof: </strong>Complete" in index
    assert "Contract:" in index
    assert "Implementation:" in index
    assert "Verification:" in index
    assert "Runtime assurance:" in index
    assert "Required evidence: impl, integration." in index
    assert "IMPL_DOCOPS" in index
    assert "1/1 current passed" in index
    assert "inspect execution path, envelope, captured boundary interactions" in index
    assert "What needs attention" not in index[index.index("Verification assurance") :]
    assert "ternforge-specification-map" in index
    assert "plotly-2.35.2.min.js" in index
    assert "Specification health" in index
    assert "GOAL_DOCOPS" in index
    assert "FEAT_DOCOPS" in index
    assert "REQ_DOCOPS" in index


def test_bdd_reader_link_targets_living_scenario_page() -> None:
    """Behavior verification links open the human Living Specifications scenario."""
    label = (
        "living-scenario-configuration-configuration-overrides-"
        "more-specific-settings-take-precedence-"
        "an-explicit-empty-value-removes-an-inherited-optional-setting"
    )
    app = SimpleNamespace(
        builder=SimpleNamespace(
            get_relative_uri=lambda source, target: f"{target}.html",
        ),
        env=SimpleNamespace(
            domaindata={
                "std": {
                    "anonlabels": {
                        label: (
                            "specifications/_generated/configuration/overrides",
                            label,
                        )
                    }
                }
            }
        ),
    )
    item = {
        "gherkin_feature": "features/configuration/overrides.feature",
        "gherkin_scenario": (
            "An explicit empty value removes an inherited optional setting"
        ),
    }

    assert (
        bdd_scenario_url(
            app,
            "traceability-reader",
            item,
        )
        == f"specifications/_generated/configuration/overrides.html#{label}"
    )


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

Verification assurance
----------------------

.. ternforge-verification-assurance-map::
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
    assert "Current proof: </strong>Incomplete" in index
    assert "Missing evidence: integration" in index
    assert "no current execution" in index


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
        ("Technical requirements", ("TREQ_DEMO",)),
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
