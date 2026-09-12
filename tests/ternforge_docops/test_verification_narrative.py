"""Tests for source-enriched verification narrative pages."""

from __future__ import annotations

import json
from pathlib import Path

from ternforge_docops._internal.verification.narrative import (
    render_verification_narratives,
    verification_anchor,
    verification_docname,
)


def _write_junit(path: Path) -> None:
    path.write_text(
        """<testsuites><testsuite name="pytest">
<testcase classname="tests.pkg.unit.test_retry" name="test_second_check">
  <properties>
    <property name="verification_kind" value="unit"/>
    <property name="verifies" value="TREQ_RETRY[revision==1]"/>
  </properties>
</testcase>
<testcase classname="tests.pkg.unit.test_retry" name="test_first_check">
  <properties>
    <property name="verification_kind" value="unit"/>
    <property name="verifies" value="TREQ_RETRY[revision==1]"/>
  </properties>
</testcase>
<testcase classname="tests.pkg.property.test_invariants" name="test_value_is_bounded">
  <properties>
    <property name="verification_kind" value="property"/>
    <property name="verifies" value="REQ_BOUNDS[revision==2]"/>
  </properties>
</testcase>
<testcase classname="tests.pkg.integration.test_http" name="test_crosses_http_boundary">
  <properties>
    <property name="verification_kind" value="integration"/>
    <property name="verifies" value="TREQ_HTTP[revision==1]"/>
  </properties>
</testcase>
<testcase classname="tests.pkg.integration.test_sdk" name="test_crosses_sdk_boundary">
  <properties>
    <property name="verification_kind" value="integration"/>
    <property name="verifies" value="TREQ_SDK[revision==1]"/>
  </properties>
</testcase>
<testcase classname="tests.pkg.e2e.test_workflow" name="test_public_workflow">
  <properties>
    <property name="verification_kind" value="e2e"/>
    <property name="verifies" value="REQ_WORKFLOW[revision==1]"/>
  </properties>
</testcase>
</testsuite></testsuites>""",
        encoding="utf-8",
    )


def test_render_verification_narratives_explains_exercise_and_checks(  # noqa: PLR0915
    tmp_path: Path,
) -> None:
    """Narrative pages explain source semantics instead of JUnit execution trivia."""
    unit = tmp_path / "tests/pkg/unit/test_retry.py"
    unit.parent.mkdir(parents=True)
    unit.write_text(
        """def classify_status_code(value):
    return value == 503


def test_first_check():
    result = classify_status_code(503)
    assert result is True


def test_second_check():
    result = classify_status_code(400)
    assert result is False
""",
        encoding="utf-8",
    )
    prop = tmp_path / "tests/pkg/property/test_invariants.py"
    prop.parent.mkdir(parents=True)
    prop.write_text(
        """from hypothesis import given, strategies as st


def normalize(value):
    return value + 1


@given(value=st.integers(min_value=0, max_value=10))
def test_value_is_bounded(value):
    observed = normalize(value)
    assert observed <= 11
""",
        encoding="utf-8",
    )
    http = tmp_path / "tests/pkg/integration/test_http.py"
    http.parent.mkdir(parents=True)
    http.write_text(
        """def test_crosses_http_boundary():
    with ScriptedHTTPServer(port=0) as server:
        result = OpenAIAdapter(server.base_url).execute(request())
    assert result.output_text == "ok"
""",
        encoding="utf-8",
    )
    sdk = tmp_path / "tests/pkg/integration/test_sdk.py"
    sdk.write_text(
        """def test_crosses_sdk_boundary():
    client = FakeClient(["ok"])
    result = GoogleAdapter(client=client).execute(request())
    assert result.output_text == "ok"
""",
        encoding="utf-8",
    )
    e2e = tmp_path / "tests/pkg/e2e/test_workflow.py"
    e2e.parent.mkdir(parents=True)
    e2e.write_text(
        """def test_public_workflow():
    with ScriptedHTTPServer(port=0) as server:
        result = LLMRouter(base_url=server.base_url).query("hello")
    assert result.output_text == "ok"
""",
        encoding="utf-8",
    )
    junit = tmp_path / "junit.xml"
    _write_junit(junit)

    pages = render_verification_narratives(tmp_path, junit)
    by_name = {page.docname: page.source for page in pages}

    unit_name = verification_docname("unit", "tests.pkg.unit.test_retry")
    unit_source = by_name[unit_name]
    assert unit_source.index("First check") < unit_source.index("Second check")
    assert "Exercise" in unit_source
    assert "classify_status_code(503)" in unit_source
    assert "Checks" in unit_source
    assert "result is True" in unit_source
    assert "Test code" in unit_source
    assert "Duration" not in unit_source
    assert "passed" not in unit_source

    property_name = verification_docname(
        "property",
        "tests.pkg.property.test_invariants",
    )
    property_source = by_name[property_name]
    assert "Property proof" in property_source
    assert (
        "Proof model:** property classification → production subject → invariant"
        in property_source
    )
    assert "Execution mechanism:** Hypothesis execution not captured" in property_source
    assert (
        "Generator declaration basis:** source-derived generator declaration"
        in property_source
    )
    assert (
        "do not by themselves prove that Hypothesis generated examples"
        in property_source
    )
    assert "Declared generators" in property_source
    assert "value = st.integers(min_value=0, max_value=10)" in property_source
    assert "Invariant" in property_source
    assert "observed <= 11" in property_source
    assert "property-classified testcase → normalize() → invariant" in property_source

    assert "Verification boundary" in unit_source
    assert "test inputs → classify_status_code()" in unit_source
    assert "Network · not exercised" in unit_source
    assert "Higher-level routing/orchestration" in unit_source

    http_source = by_name[
        verification_docname("integration", "tests.pkg.integration.test_http")
    ]
    assert "real HTTP client → localhost HTTP ┃ live provider" in http_source
    assert "Network · localhost HTTP" in http_source
    assert "External · scripted provider" in http_source
    assert "live provider/service → local ScriptedHTTPServer" in http_source

    sdk_source = by_name[
        verification_docname("integration", "tests.pkg.integration.test_sdk")
    ]
    assert "FakeClient → real SDK/network/provider" in sdk_source
    assert "External · FakeClient test double" in sdk_source
    assert "real SDK/provider client → FakeClient" in sdk_source

    e2e_source = by_name[verification_docname("e2e", "tests.pkg.e2e.test_workflow")]
    assert (
        "public workflow → production stack → HTTP client → localhost HTTP "
        "┃ live external provider" in e2e_source
    )
    assert "Live external-provider fidelity" in e2e_source
    assert "End-to-end reach" in e2e_source
    assert "Terminal interactions:** no captured boundary interaction" in e2e_source
    assert "Live external-system fidelity is claimed only when" in e2e_source


def test_verification_narrative_identity_is_stable() -> None:
    """Reader links and generated pages share one deterministic identity scheme."""
    classname = "tests.pkg.integration.test_boundary"
    name = "test_request_crosses_boundary"

    assert (
        verification_docname(
            "integration",
            classname,
        )
        == "verification/_generated/integration/tests-pkg-integration-test-boundary"
    )
    assert verification_anchor(
        "integration",
        classname,
        name,
    ) == (
        "verification-integration-tests-pkg-integration-test-boundary-"
        "test-request-crosses-boundary"
    )


def test_runtime_evidence_overrides_source_fallback_for_boundary(
    tmp_path: Path,
) -> None:
    """Captured execution facts outrank source inspection in assurance semantics."""
    source = tmp_path / "tests/pkg/integration/test_adapter.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        """def test_provider_boundary():
    with ScriptedHTTPServer(port=0) as server:
        result = Adapter(server.base_url).execute(request())
    assert result.output_text == "ok"
""",
        encoding="utf-8",
    )
    junit = tmp_path / "junit.xml"
    junit.write_text(
        """<testsuites><testsuite name="pytest">
<testcase classname="tests.pkg.integration.test_adapter" name="test_provider_boundary">
  <properties>
    <property name="verification_kind" value="integration"/>
    <property name="verifies" value="TREQ_PROVIDER[revision==1]"/>
  </properties>
</testcase>
</testsuite></testsuites>""",
        encoding="utf-8",
    )
    allure = tmp_path / "allure-results"
    allure.mkdir()
    observation = allure / "execution.json"
    observation.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "test-execution",
                "payload": {
                    "nodeid": (
                        "tests/pkg/integration/test_adapter.py::test_provider_boundary"
                    ),
                    "path": "tests/pkg/integration/test_adapter.py",
                    "verification_kind": "integration",
                    "fixtures": [],
                    "markers": ["vcr"],
                },
            }
        ),
        encoding="utf-8",
    )
    (allure / "result-result.json").write_text(
        json.dumps(
            {
                "uuid": "result",
                "name": "test_provider_boundary",
                "fullName": "tests.pkg.integration.test_adapter#test_provider_boundary",
                "start": 1,
                "stop": 2,
                "attachments": [
                    {
                        "name": "Ternforge test execution",
                        "type": (
                            "application/vnd.ternforge.verification-observation+json"
                        ),
                        "source": observation.name,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    coverage = tmp_path / "coverage.json"
    coverage.write_text(
        json.dumps(
            {
                "files": {
                    "src/pkg/adapter.py": {
                        "contexts": {
                            "20": [
                                (
                                    "tests/pkg/integration/test_adapter.py::"
                                    "test_provider_boundary|run"
                                )
                            ],
                            "21": [
                                (
                                    "tests/pkg/integration/test_adapter.py::"
                                    "test_provider_boundary|run"
                                )
                            ],
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    pages = render_verification_narratives(
        tmp_path,
        junit,
        allure_results=allure,
        coverage=coverage,
    )
    page = pages[0].source

    assert "adapter → HTTP client ┃ retained VCR replay → live provider" in page
    assert "Network · recorded HTTP replay" in page
    assert "External · recorded provider interaction" in page
    assert "live HTTP interaction → retained VCR replay" in page
    assert "Boundary basis:** captured runtime evidence" in page
    assert "local ScriptedHTTPServer" not in page


def test_property_narrative_distinguishes_runtime_hypothesis_from_source_domain(
    tmp_path: Path,
) -> None:
    """Property assurance separates runtime Hypothesis evidence from source domain."""
    source = tmp_path / "tests/pkg/property/test_invariants.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        """from hypothesis import given, strategies as st


def normalize(value):
    return value + 1


@given(value=st.integers(min_value=0, max_value=10))
def test_value_is_bounded(value):
    observed = normalize(value)
    assert observed <= 11
""",
        encoding="utf-8",
    )
    junit = tmp_path / "junit.xml"
    junit.write_text(
        """<testsuites><testsuite name="pytest">
<testcase classname="tests.pkg.property.test_invariants" name="test_value_is_bounded">
  <properties>
    <property name="verification_kind" value="property"/>
    <property name="verifies" value="REQ_BOUNDS[revision==2]"/>
  </properties>
</testcase>
</testsuite></testsuites>""",
        encoding="utf-8",
    )
    allure = tmp_path / "allure-results"
    allure.mkdir()
    observation = allure / "execution.json"
    nodeid = "tests/pkg/property/test_invariants.py::test_value_is_bounded"
    observation.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "test-execution",
                "payload": {
                    "nodeid": nodeid,
                    "path": "tests/pkg/property/test_invariants.py",
                    "verification_kind": "property",
                    "fixtures": [],
                    "markers": ["hypothesis"],
                },
            }
        ),
        encoding="utf-8",
    )
    (allure / "result-result.json").write_text(
        json.dumps(
            {
                "uuid": "result",
                "name": "test_value_is_bounded",
                "fullName": "tests.pkg.property.test_invariants#test_value_is_bounded",
                "start": 1,
                "stop": 2,
                "attachments": [
                    {
                        "name": "Ternforge test execution",
                        "type": (
                            "application/vnd.ternforge.verification-observation+json"
                        ),
                        "source": observation.name,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    coverage = tmp_path / "coverage.json"
    coverage.write_text(
        json.dumps(
            {
                "files": {
                    "src/pkg/normalize.py": {
                        "contexts": {
                            "20": [f"{nodeid}|run"],
                            "21": [f"{nodeid}|run"],
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    pages = render_verification_narratives(
        tmp_path,
        junit,
        allure_results=allure,
        coverage=coverage,
    )
    page = pages[0].source

    assert "Captured runtime evidence confirms Hypothesis execution" in page
    assert (
        "Proof model:** Hypothesis generated examples → production subject → invariant"
        in page
    )
    assert "Execution mechanism:** Hypothesis · captured runtime evidence" in page
    assert "Generator declaration basis:** source-derived generator declaration" in page
    assert "Hypothesis generated domain → normalize → invariant" in page
    assert (
        "Boundary basis:** captured runtime evidence + source-derived generator "
        "declaration" in page
    )
    assert "Hypothesis execution not captured" not in page
