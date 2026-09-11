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
