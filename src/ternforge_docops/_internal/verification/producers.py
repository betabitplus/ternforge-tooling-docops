"""Evidence-producer identities carried from runtime facts into the Needs graph."""

from __future__ import annotations

from ternforge_docops._internal.verification.evidence import VerificationRuntimeEvidence

PRODUCER_PYTEST = "PRODUCER_PYTEST"
PRODUCER_PYTEST_BDD = "PRODUCER_PYTEST_BDD"
PRODUCER_HYPOTHESIS = "PRODUCER_HYPOTHESIS"
PRODUCER_ALLURE = "PRODUCER_ALLURE"
PRODUCER_PY_TESTKIT = "PRODUCER_PY_TESTKIT"
PRODUCER_VCR = "PRODUCER_VCR"
PRODUCER_SCRIPTED_HTTP_SERVER = "PRODUCER_SCRIPTED_HTTP_SERVER"
PRODUCER_JUNIT_IMPORTER = "PRODUCER_JUNIT_IMPORTER"
PRODUCER_REVISION_RESOLVER = "PRODUCER_REVISION_RESOLVER"
PRODUCER_VERIFICATION_NARRATIVE = "PRODUCER_VERIFICATION_NARRATIVE"
PRODUCER_LIVING_SPECS = "PRODUCER_LIVING_SPECS"


def _payload_producer_ids(payload: dict[str, object]) -> tuple[str, ...]:
    """Read one or many stable producer IDs from a runtime observation."""
    raw = payload.get("producer_ids")
    values = raw if isinstance(raw, list) else [payload.get("producer_id")]
    return tuple(
        value
        for item in values
        if isinstance(item, str) and (value := item.strip()).startswith("PRODUCER_")
    )


def _declared_producer_ids(
    runtime: VerificationRuntimeEvidence | None,
) -> tuple[str, ...]:
    """Read producer IDs explicitly published by the coordinated evidence transport."""
    if runtime is None:
        return ()
    values = [
        producer_id
        for observation in runtime.observations
        for producer_id in _payload_producer_ids(observation.payload)
    ]
    return tuple(dict.fromkeys(values))


def evidence_producer_ids(
    runtime: VerificationRuntimeEvidence | None,
    *,
    gherkin_feature: str = "",
) -> tuple[str, ...]:
    """Return producer links only when the runtime transport declares their IDs."""
    values = list(_declared_producer_ids(runtime))
    execution = None if runtime is None else runtime.execution
    transport_ids = (
        () if execution is None else _payload_producer_ids(execution.payload)
    )
    if not transport_ids:
        return tuple(dict.fromkeys(values))

    values.extend(transport_ids)
    values.extend((PRODUCER_JUNIT_IMPORTER, PRODUCER_REVISION_RESOLVER))
    values.append(
        PRODUCER_LIVING_SPECS
        if gherkin_feature.strip()
        else PRODUCER_VERIFICATION_NARRATIVE
    )
    return tuple(dict.fromkeys(values))
