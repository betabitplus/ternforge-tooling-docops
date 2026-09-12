"""Tests for shared verification-assurance semantics."""

from __future__ import annotations

from ternforge_docops._internal.verification.assurance import runtime_assurance_facts
from ternforge_docops._internal.verification.coverage_evidence import (
    CoverageFile,
    CoverageFootprint,
)
from ternforge_docops._internal.verification.evidence import (
    VerificationObservation,
    VerificationRuntimeEvidence,
)


def _runtime(*observations: VerificationObservation) -> VerificationRuntimeEvidence:
    return VerificationRuntimeEvidence(
        nodeid="tests/pkg/test_provider.py::test_boundary",
        observations=(
            VerificationObservation(
                name="execution",
                kind="test-execution",
                payload={
                    "nodeid": "tests/pkg/test_provider.py::test_boundary",
                    "path": "tests/pkg/test_provider.py",
                    "verification_kind": "integration",
                    "fixtures": [],
                    "markers": ["vcr", "hermetic"],
                },
            ),
            *observations,
        ),
    )


def test_explicit_sdk_substitute_outranks_generic_vcr_marker() -> None:
    """A producer-recorded boundary fact is stronger than a generic test marker."""
    runtime = _runtime(
        VerificationObservation(
            name="Google SDK substitute",
            kind="external-substitute",
            payload={
                "producer": "GoogleGenAIFakeClient",
                "boundary": "provider-sdk",
                "mode": "in-process-fake-sdk",
                "transport": "SDK surface",
                "target": "Google GenAI SDK/provider",
            },
        )
    )
    coverage = CoverageFootprint(
        nodeid=runtime.nodeid,
        files=(
            CoverageFile(
                path="src/pkg/_internal/providers/google_genai.py",
                lines=(10, 11, 12),
                phases=("run",),
            ),
        ),
    )

    facts = runtime_assurance_facts(runtime, coverage)

    assert facts is not None
    assert facts.mechanism == "external-double"
    assert facts.modules == ("providers.google_genai",)
    assert facts.network == "substituted SDK surface"
    assert facts.external == "GoogleGenAIFakeClient test double"
    assert facts.substitutes[0].target == "Google GenAI SDK/provider"
    assert facts.interactions[0].interaction == "substitute"
    assert facts.interactions[0].participant == "GoogleGenAIFakeClient"
    assert facts.interactions[0].target == "Google GenAI SDK/provider"
    assert facts.provenance == "captured runtime evidence"


def test_explicit_http_substitute_outranks_generic_vcr_marker() -> None:
    """A captured local HTTP substitute wins over incidental VCR configuration."""
    runtime = _runtime(
        VerificationObservation(
            name="Provider HTTP substitute",
            kind="external-substitute",
            payload={
                "producer": "ScriptedHTTPServer",
                "boundary": "provider-http",
                "mode": "local-scripted-http",
                "transport": "HTTP",
                "target": "live-provider",
            },
        )
    )

    facts = runtime_assurance_facts(runtime, None)

    assert facts is not None
    assert facts.mechanism == "scripted-http"
    assert facts.network == "localhost HTTP"
    assert facts.external == "scripted provider"
    assert facts.interactions[0].boundary == "provider-http"
    assert facts.interactions[0].interaction == "substitute"


def _typed_runtime(
    *,
    verification_kind: str,
    interaction: str,
    transport: str,
) -> VerificationRuntimeEvidence:
    """Build runtime evidence around one explicitly captured boundary interaction."""
    nodeid = "tests/pkg/test_provider.py::test_boundary"
    return VerificationRuntimeEvidence(
        nodeid=nodeid,
        observations=(
            VerificationObservation(
                name="execution",
                kind="test-execution",
                payload={
                    "nodeid": nodeid,
                    "path": "tests/pkg/test_provider.py",
                    "verification_kind": verification_kind,
                    "fixtures": [],
                    "markers": [],
                },
            ),
            VerificationObservation(
                name="provider boundary",
                kind="boundary-interaction",
                payload={
                    "boundary": "provider-http",
                    "interaction": interaction,
                    "participant": "HTTP client",
                    "target": "live provider",
                    "transport": transport,
                },
            ),
        ),
    )


def test_generic_http_substitute_is_not_misclassified_as_scripted_server() -> None:
    """A provider HTTP boundary alone does not identify its substitute."""
    nodeid = "tests/pkg/test_provider.py::test_boundary"
    runtime = VerificationRuntimeEvidence(
        nodeid=nodeid,
        observations=(
            VerificationObservation(
                name="execution",
                kind="test-execution",
                payload={
                    "nodeid": nodeid,
                    "path": "tests/pkg/test_provider.py",
                    "verification_kind": "integration",
                    "fixtures": [],
                    "markers": [],
                },
            ),
            VerificationObservation(
                name="provider boundary",
                kind="boundary-interaction",
                payload={
                    "boundary": "provider-http",
                    "interaction": "substitute",
                    "participant": "ProxyStub",
                    "target": "live provider",
                    "transport": "HTTP",
                },
            ),
        ),
    )

    facts = runtime_assurance_facts(runtime, None)

    assert facts is not None
    assert facts.mechanism == "external-double"
    assert facts.network == "substituted HTTP"
    assert facts.external == "ProxyStub test double"


def test_direct_boundary_interaction_is_explicit_runtime_fact() -> None:
    """Direct external participation is not inferred from an integration label."""
    facts = runtime_assurance_facts(
        _typed_runtime(
            verification_kind="e2e",
            interaction="direct",
            transport="HTTPS",
        ),
        None,
    )

    assert facts is not None
    assert facts.mechanism == "boundary-direct"
    assert facts.network == "direct HTTPS"
    assert facts.external == "direct live provider"
    assert facts.interactions[0].participant == "HTTP client"


def test_replay_boundary_interaction_is_distinct_from_direct_external_reach() -> None:
    """A retained replay is explicit evidence but never a live external interaction."""
    facts = runtime_assurance_facts(
        _typed_runtime(
            verification_kind="e2e",
            interaction="replay",
            transport="HTTP",
        ),
        None,
    )

    assert facts is not None
    assert facts.mechanism == "boundary-replay"
    assert facts.network == "replayed HTTP"
    assert facts.external == "replayed live provider"


def test_multiple_boundary_interactions_are_not_collapsed_by_summary() -> None:
    """Independent substitute and direct interactions remain visible together."""
    runtime = _runtime(
        VerificationObservation(
            name="provider SDK boundary",
            kind="boundary-interaction",
            payload={
                "boundary": "provider-sdk",
                "interaction": "substitute",
                "participant": "ProxyStub",
                "target": "live provider",
                "transport": "SDK",
            },
        ),
        VerificationObservation(
            name="telemetry boundary",
            kind="boundary-interaction",
            payload={
                "boundary": "telemetry-http",
                "interaction": "direct",
                "participant": "HTTP client",
                "target": "telemetry service",
                "transport": "HTTPS",
            },
        ),
    )

    facts = runtime_assurance_facts(runtime, None)

    assert facts is not None
    assert facts.mechanism == "external-double"
    assert len(facts.interactions) == 2
    assert facts.network == "substituted SDK; direct HTTPS"
    assert facts.external == "ProxyStub test double; direct telemetry service"
