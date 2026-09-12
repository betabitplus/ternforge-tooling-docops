"""Runtime-assurance projection for Living Specifications boundaries."""

from __future__ import annotations

from ternforge_docops._internal.verification.assurance import RuntimeAssuranceFacts


def _external_double_details(
    facts: RuntimeAssuranceFacts,
) -> tuple[str, str, str, str]:
    """Describe an explicitly captured external test double."""
    producers = ", ".join(item.producer for item in facts.substitutes)
    targets = ", ".join(
        dict.fromkeys(item.target for item in facts.substitutes if item.target)
    )
    target = targets or "external SDK/provider"
    return (
        f"production code ┃ {producers} → {target}",
        (
            "Production application/provider mapping executes against the captured "
            "external client surface."
        ),
        f"{target} is replaced by {producers} for this execution.",
        (
            "The real external client implementation, network transport, "
            "authentication, and remote-provider behavior."
        ),
    )


def captured_boundary_details(
    kind: str,
    facts: RuntimeAssuranceFacts | None,
) -> tuple[str, str, str, str] | None:
    """Return detail text only for first-class captured boundary semantics."""
    if kind == "external-double" and facts is not None:
        return _external_double_details(facts)
    if kind == "boundary-replay":
        return (
            "production code ┃ captured boundary replay → external system",
            "Production code executes to the explicitly captured replay interaction.",
            (
                "The terminal external interaction is supplied by captured replay "
                "evidence."
            ),
            "Current external-system behavior beyond the captured replay.",
        )
    if kind == "boundary-direct":
        return (
            "production code → live external boundary",
            (
                "Production code executes through an explicitly captured direct "
                "external interaction."
            ),
            "No substitute is recorded for the captured direct interaction.",
            (
                "External behavior outside this captured run and "
                "deployment/environment differences."
            ),
        )
    return None


def observed_path(path: str, facts: RuntimeAssuranceFacts | None) -> str:
    """Replace generic production-code wording with modules observed at runtime."""
    if facts is None or not facts.modules:
        return path
    return path.replace("production code", " → ".join(facts.modules), 1)


def runtime_labels(
    facts: RuntimeAssuranceFacts | None,
) -> tuple[str, str, str, str, str]:
    """Return presentation labels for captured runtime facts or fallback state."""
    if facts is None:
        return (
            "not captured",
            "not captured",
            "not captured",
            "not captured",
            "source-derived fallback",
        )
    return (
        facts.process,
        facts.network or "not explicit",
        facts.filesystem,
        facts.external or "not explicit",
        facts.provenance,
    )
