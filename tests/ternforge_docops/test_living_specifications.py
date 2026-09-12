"""Hermetic tests for native Living Specifications presentation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ternforge_docops._internal.living_specs import (
    publish_living_assets,
    render_living_specifications,
)
from ternforge_docops._internal.living_specs.boundary import infer_boundary
from ternforge_docops._internal.living_specs.models import (
    LivingImplementation,
    LivingStep,
)
from ternforge_docops._internal.verification.coverage_evidence import (
    CoverageFile,
    CoverageFootprint,
)
from ternforge_docops._internal.verification.evidence import (
    VerificationObservation,
    VerificationRuntimeEvidence,
)

_BDD_IMPLEMENTATION_TYPE = "application/vnd.ternforge.bdd-implementation+json"
_CONTRACT_TYPE = "application/vnd.ternforge.contract+json"


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
                    {
                        "name": 'Given the "QwenChat" image route',
                        "status": status,
                        "attachments": [
                            {
                                "name": "Ternforge BDD implementation",
                                "source": "given-implementation.json",
                                "type": _BDD_IMPLEMENTATION_TYPE,
                            }
                        ],
                    },
                    {
                        "name": "When the route analyzes the example traffic image:",
                        "status": status,
                        "attachments": [
                            {
                                "name": "Ternforge BDD implementation",
                                "source": "when-implementation.json",
                                "type": _BDD_IMPLEMENTATION_TYPE,
                            },
                            {
                                "name": "Response schema",
                                "source": "schema-contract.json",
                                "type": _CONTRACT_TYPE,
                            },
                            {
                                "name": "Tool · add",
                                "source": "tool-contract.json",
                                "type": _CONTRACT_TYPE,
                            },
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
                                "name": "Ternforge BDD implementation",
                                "source": "then-implementation.json",
                                "type": _BDD_IMPLEMENTATION_TYPE,
                            },
                            {
                                "name": "Result",
                                "source": "result.json",
                                "type": "application/json",
                            },
                        ],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def _write_implementation(
    path: Path,
    *,
    keyword: str,
    text: str,
    function: str,
    source: str,
    start_line: int,
) -> None:
    """Write one py-testkit BDD implementation attachment fixture."""
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "keyword": keyword,
                "text": text,
                "function": function,
                "path": "tests/bdd/test_images.py",
                "start_line": start_line,
                "end_line": start_line + len(source.splitlines()) - 1,
                "source": source,
            }
        ),
        encoding="utf-8",
    )


def _prepare_rich_evidence_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path]:
    """Create the consumer repository shell used by the rich-evidence fixture."""
    root = tmp_path / "repo"
    raw = root / "allure-results"
    feature = root / "features" / "structured_output" / "images.feature"
    raw.mkdir(parents=True)
    feature.parent.mkdir(parents=True)
    feature.write_text("Feature: Structured image understanding\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        (
            '[project]\nname = "demo"\n'
            '[project.urls]\nRepository = "https://github.com/acme/demo"\n'
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("GITHUB_SHA", "1111111111111111111111111111111111111111")
    return root, raw


def _write_implementation_fixtures(raw: Path) -> None:
    """Write exact Given/When/Then binding evidence for the report fixture."""
    _write_implementation(
        raw / "given-implementation.json",
        keyword="Given",
        text='the "QwenChat" image route',
        function="provider_image_route",
        source=(
            '@given("the QwenChat image route")\n'
            "def provider_image_route():\n"
            "    return LLMRouter(...)"
        ),
        start_line=20,
    )
    _write_implementation(
        raw / "when-implementation.json",
        keyword="When",
        text="the route analyzes the example traffic image:",
        function="analyze_image",
        source=(
            '@when("the route analyzes the example traffic image:")\n'
            "def analyze_image(router, docstring):\n"
            '    return router.query(docstring, images=["traffic.png"])'
        ),
        start_line=30,
    )
    _write_implementation(
        raw / "then-implementation.json",
        keyword="Then",
        text="the result is a grounded traffic scene",
        function="grounded_result",
        source=(
            '@then("the result is a grounded traffic scene")\n'
            "def grounded_result(response):\n"
            "    assert response.output_text"
        ),
        start_line=40,
    )


def _write_contract_fixtures(raw: Path) -> None:
    """Write one live schema and callable contract captured by py-testkit."""
    (raw / "schema-contract.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "name": "Response schema",
                "kind": "schema",
                "qualified_name": "tests.support.SceneSummary",
                "description": (
                    "Grounded scene response.\n\n"
                    "Attributes:\n"
                    "    setting: The grounded scene setting."
                ),
                "schema": {
                    "title": "SceneSummary",
                    "type": "object",
                    "properties": {"setting": {"type": "string"}},
                },
            }
        ),
        encoding="utf-8",
    )
    (raw / "tool-contract.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "name": "Tool · add",
                "kind": "callable",
                "qualified_name": "tests.tools.add",
                "description": "Add two integers.",
                "signature": "(a: int, b: int) -> dict[str, int]",
            }
        ),
        encoding="utf-8",
    )


def _write_rich_evidence_files(raw: Path) -> None:
    """Write current/obsolete execution evidence and retained user-facing assets."""
    (raw / "prompt.txt").write_text("Describe the attached image.", encoding="utf-8")
    (raw / "result.json").write_text('{"setting":"highway"}', encoding="utf-8")
    (raw / "input.png").write_bytes(b"png")
    _write_result(raw / "old-result.json", stop=100, status="failed")
    _write_result(raw / "current-result.json", stop=200, status="passed")


def _assert_rich_feature_page(  # noqa: PLR0915
    docname: str,
    source: str,
) -> None:
    """Assert the layered feature-page narrative generated from rich evidence."""
    assert docname == "specifications/_generated/structured-output/images"
    assert "Structured image understanding" in source
    assert "The same image contract should remain valid" in source
    assert ":bdg-success:`Verified` **1/1 passed**" in source
    assert ":need:`REQ_IMAGE_INPUT`" in source
    assert ".. dropdown:: Contract provenance" in source
    assert ".. ternforge-contract-provenance:: REQ_IMAGE_INPUT" in source
    assert ".. card:: Verification boundary" in source
    assert (
        "**Path:** ``LLMRouter.query → production code ┃ hermetic local resources``"
        in source
    )
    assert "**Real path:**" in source
    assert "**Substitute:**" in source
    assert "**Not covered:**" in source
    assert ".. dropdown:: How this scenario establishes the proof" in source
    assert "**Injected condition:**" in source
    assert "**Observed proof:**" in source
    assert ".. tab-item:: ✓ QwenChat" in source
    assert (
        ":bdg-link-secondary-line:`Execution evidence ↗ "
        "<../../../test-results/index.html#abc123>`" in source
    )
    assert ".. rubric:: Scenarios" in source
    assert (
        ".. dropdown:: Scenario 01 · A provider route describes the example "
        "traffic image" in source
    )
    assert ":open:" in source
    assert "Rule · A traffic image produces grounded structured evidence" in source
    assert ":bdg-secondary-line:`Rule`" not in source
    assert ":shadow: none" not in source
    assert ":margin:" not in source
    assert ".. container:: living-scenario" not in source
    assert ".. container:: living-step" not in source
    assert ":class-card: portal-card" not in source
    assert "**Executed:**" in source
    assert '**Given** the "QwenChat" image route' in source
    assert "**When** the route analyzes the example traffic image:" in source
    assert source.count("Implementation ↗") == 3
    assert (
        "https://github.com/acme/demo/blob/1111111111111111111111111111111111111111/"
        "tests/bdd/test_images.py#L30-L32" in source
    )
    assert ".. dropdown:: Executable usage" in source
    assert "exact pytest-bdd binding executed" in source
    assert 'return router.query(docstring, images=["traffic.png"])' in source
    assert ".. dropdown:: Public contract" in source
    assert "Derived from the exact schema classes and callables" in source
    assert "**Response schema**" in source
    assert "``SceneSummary``" in source
    assert "``tests.support.SceneSummary``" not in source
    assert (
        "Grounded scene response. Attributes: setting: The grounded scene setting."
        in source
    )
    assert '"title": "SceneSummary"' in source
    assert "**Tool · add**" in source
    assert "``add``" in source
    assert "``tests.tools.add``" not in source
    assert "add(a: int, b: int) -> dict[str, int]" in source
    assert "**Prompt**" in source
    assert "Describe the attached image." in source
    assert ".. card:: Observed outcome" in source
    assert "**setting:** highway" in source
    assert ".. dropdown:: Raw captured result" in source
    assert ".. code-block:: json" in source
    assert ".. data-viewer::" not in source
    assert ".. dropdown:: Technical details" in source
    assert ".. dropdown:: Gherkin source" in source
    assert (
        ".. literalinclude:: ../../../../features/structured_output/images.feature"
        in source
    )


def test_living_specs_render_current_narrative_and_rich_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The latest execution becomes one decision-first feature narrative."""
    root, raw = _prepare_rich_evidence_repository(tmp_path, monkeypatch)
    _write_implementation_fixtures(raw)
    _write_contract_fixtures(raw)
    _write_rich_evidence_files(raw)
    result_links = {
        (
            "tests.bdd.test_images#test_image",
            180,
            "A provider route describes the example traffic image — QwenChat",
        ): "test-results/index.html#abc123"
    }

    report = render_living_specifications(root, raw, result_links=result_links)

    assert "Capabilities by area" in report.source
    assert ".. _living-specs-area-structured-output:" in report.source
    assert "Structured Output" in report.source
    assert (
        ":doc:`Structured image understanding "
        "<specifications/_generated/structured-output/images>`" in report.source
    )
    assert "Describe the attached image." not in report.source
    assert len(report.pages) == 1
    page = report.pages[0]
    _assert_rich_feature_page(page.docname, page.source)
    assert [asset.output_name for asset in report.assets] == ["input.png"]


def _boundary_step(
    name: str,
    *,
    source: str,
    path: str = "tests/bdd/test_demo.py",
) -> LivingStep:
    """Create one captured BDD step for boundary-inference tests."""
    return LivingStep(
        name=name,
        status="passed",
        attachments=(),
        implementation=LivingImplementation(
            keyword=name.split(" ", 1)[0],
            text=name.partition(" ")[2],
            function="step_impl",
            path=path,
            start_line=1,
            end_line=max(1, len(source.splitlines())),
            source=source,
        ),
    )


def test_boundary_uses_exact_scripted_http_binding() -> None:
    """A local scripted provider is explicit even when the scenario is hermetic."""
    steps = (
        _boundary_step(
            "Given a provider rejects a request permanently",
            source=(
                "def given():\n"
                "    return [\n"
                "        ScriptedResponse(status_code=400),\n"
                "        ScriptedResponse(status_code=200),\n"
                "    ]"
            ),
        ),
        _boundary_step(
            "When the request is executed",
            source=(
                "def run(case):\n"
                "    with ScriptedHTTPServer(port=0) as server:\n"
                "        return run_retry_worker(server_base_url=server.base_url)"
            ),
        ),
        _boundary_step(
            "Then the provider is not retried",
            source=(
                "def then(result, case):\n"
                "    assert result.ok is False\n"
                "    assert result.error_type == 'ProviderError'\n"
                "    assert case['request_count'] == 1"
            ),
        ),
    )

    boundary = infer_boundary(tags=("hermetic",), steps=steps)

    assert boundary is not None
    assert boundary.path == (
        "run_retry_worker → production code → HTTP client ┃ scripted HTTP server"
    )
    assert "ScriptedHTTPServer" in boundary.substitute
    assert "Live provider infrastructure" in boundary.not_covered
    assert boundary.injected_condition == (
        "a provider rejects a request permanently · scripted HTTP responses: 400 → 200"
    )
    assert boundary.observed_proof == (
        "the provider is not retried · public result fails · "
        "ProviderError · 1 provider request"
    )


def test_boundary_uses_explicit_vcr_tag() -> None:
    """An explicit VCR scenario reports replay rather than generic hermetic scope."""
    steps = (
        _boundary_step("Given a recorded provider case", source="def given(): pass"),
        _boundary_step(
            "When the route executes",
            source="def run(router):\n    return router.query('hello')",
        ),
        _boundary_step("Then the response is normalized", source="def then(): pass"),
    )

    boundary = infer_boundary(tags=("hermetic", "vcr"), steps=steps)

    assert boundary is not None
    assert boundary.path == (
        "LLMRouter.query → production code → HTTP client ┃ recorded HTTP replay"
    )
    assert "VCR" in boundary.substitute
    assert "live-provider availability" in boundary.not_covered


def test_boundary_prefers_captured_runtime_evidence_over_source_guessing() -> None:
    """Runtime substitute and coverage facts override contradictory source hints."""
    steps = (
        _boundary_step(
            "Given a provider case",
            source="def given(): return ScriptedResponse(status_code=200)",
        ),
        _boundary_step(
            "When the route executes",
            source=(
                "def run(router):\n"
                "    with ScriptedHTTPServer(port=0) as server:\n"
                "        return router.query('hello')"
            ),
        ),
        _boundary_step(
            "Then the response is normalized",
            source="def then(result): assert result.ok is True",
        ),
    )
    runtime = VerificationRuntimeEvidence(
        nodeid="tests/bdd/test_demo.py::test_route",
        observations=(
            VerificationObservation(
                name="Ternforge test execution",
                kind="test-execution",
                payload={
                    "nodeid": "tests/bdd/test_demo.py::test_route",
                    "path": "tests/bdd/test_demo.py",
                    "verification_kind": "bdd",
                    "fixtures": [],
                    "markers": ["vcr", "hermetic"],
                },
            ),
        ),
    )
    coverage = CoverageFootprint(
        nodeid=runtime.nodeid,
        files=(
            CoverageFile(
                path="src/demo/_internal/runtime/router.py",
                lines=(10, 11, 12),
                phases=("run",),
            ),
            CoverageFile(
                path="src/demo/_internal/providers/openai.py",
                lines=(20, 21),
                phases=("run",),
            ),
        ),
    )

    boundary = infer_boundary(
        tags=("hermetic",),
        steps=steps,
        runtime=runtime,
        coverage=coverage,
    )

    assert boundary is not None
    assert boundary.path == (
        "LLMRouter.query → runtime.router → providers.openai → HTTP client ┃ "
        "recorded HTTP replay"
    )
    assert "VCR" in boundary.substitute
    assert boundary.network == "recorded HTTP replay"
    assert boundary.external == "recorded provider interaction"
    assert boundary.provenance == "captured runtime evidence"
    assert "scripted HTTP server" not in boundary.path


def test_boundary_uses_typed_direct_external_interaction() -> None:
    """A direct interaction is runtime evidence, not an E2E/integration guess."""
    steps = (
        _boundary_step("Given a provider case", source="def given(): pass"),
        _boundary_step(
            "When the route executes",
            source="def run(router):\n    return router.query('hello')",
        ),
        _boundary_step("Then the response is normalized", source="def then(): pass"),
    )
    nodeid = "tests/bdd/test_demo.py::test_route"
    runtime = VerificationRuntimeEvidence(
        nodeid=nodeid,
        observations=(
            VerificationObservation(
                name="Ternforge test execution",
                kind="test-execution",
                payload={
                    "nodeid": nodeid,
                    "path": "tests/bdd/test_demo.py",
                    "verification_kind": "bdd",
                    "fixtures": [],
                    "markers": [],
                },
            ),
            VerificationObservation(
                name="provider-http boundary interaction",
                kind="boundary-interaction",
                payload={
                    "boundary": "provider-http",
                    "interaction": "direct",
                    "participant": "HTTP client",
                    "target": "live provider",
                    "transport": "HTTPS",
                },
            ),
        ),
    )

    boundary = infer_boundary(tags=(), steps=steps, runtime=runtime)

    assert boundary is not None
    assert boundary.path == "LLMRouter.query → production code → live external boundary"
    assert boundary.network == "direct HTTPS"
    assert boundary.external == "direct live provider"
    assert boundary.interactions[0].interaction == "direct"
    assert "No substitute is recorded" in boundary.substitute


def test_living_specs_publish_only_linked_binary_assets(tmp_path: Path) -> None:
    """Inline JSON/text stay in the page while media is published beside it."""
    root = tmp_path / "repo"
    raw = root / "allure-results"
    feature = root / "features" / "structured_output" / "images.feature"
    raw.mkdir(parents=True)
    feature.parent.mkdir(parents=True)
    feature.write_text("Feature: Structured image understanding\n", encoding="utf-8")
    (raw / "prompt.txt").write_text("prompt", encoding="utf-8")
    (raw / "result.json").write_text(
        '{"message":"provider\u0027s response"}', encoding="utf-8"
    )
    (raw / "input.png").write_bytes(b"image-bytes")
    _write_result(raw / "fixture-result.json", stop=200, status="passed")
    report = render_living_specifications(root, raw)
    output = tmp_path / "site"

    assert "provider's response" in report.pages[0].source
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
