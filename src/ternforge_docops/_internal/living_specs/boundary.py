"""Verification-boundary inference for Living Specifications."""

from __future__ import annotations

import ast
import re

from ternforge_docops._internal.living_specs.assurance_boundary import (
    captured_boundary_details as _captured_boundary_details,
    observed_path as _observed_path,
    runtime_labels as _runtime_labels,
)
from ternforge_docops._internal.living_specs.models import (
    LivingStep,
    LivingVerificationBoundary,
)
from ternforge_docops._internal.verification.assurance import (
    RuntimeAssuranceFacts,
    runtime_assurance_facts,
)
from ternforge_docops._internal.verification.coverage_evidence import CoverageFootprint
from ternforge_docops._internal.verification.evidence import VerificationRuntimeEvidence

_MAX_SENTENCE_PARTS = 2

_SCRIPTED_HTTP = "ScriptedHTTPServer"
_TMP_PATH = "tmp_path"
_STATUS_CODE_RE = re.compile(r"status_code\s*=\s*(\d{3})")
_ERROR_TYPE_RE = re.compile(r"error_type\s*==\s*[\"']([^\"']+)[\"']")
_REQUEST_COUNT_RE = re.compile(r"[\"']request_count[\"']\]\s*==\s*(\d+)")
_RESULT_OK_RE = re.compile(r"result\.ok\s+is\s+(True|False)")


def _step_parts(name: str) -> tuple[str, str]:
    """Split a captured BDD step into keyword and sentence."""
    first, separator, rest = name.partition(" ")
    if first in {"Given", "When", "Then", "And", "But"}:
        return first, rest if separator else ""
    return "Step", name


def _compact_sentences(values: list[str]) -> str:
    """Join a few scenario sentences without turning the card into prose."""
    unique = list(dict.fromkeys(value for value in values if value))
    shown = unique[:_MAX_SENTENCE_PARTS]
    text = "; ".join(shown)
    if len(unique) > len(shown):
        text = f"{text}; …"
    return text


def _append_facts(text: str, facts: list[str]) -> str:
    """Append a few source-derived facts without repeating code."""
    compact = list(dict.fromkeys(fact for fact in facts if fact))
    suffix = " · ".join(compact[:3])
    if text and suffix:
        return f"{text} · {suffix}"
    return text or suffix


def _given_source_facts(source: str) -> list[str]:
    """Extract injected HTTP conditions from exact Given binding source."""
    status_codes = list(dict.fromkeys(_STATUS_CODE_RE.findall(source)))
    if not status_codes:
        return []
    noun = "response" if len(status_codes) == 1 else "responses"
    return [f"scripted HTTP {noun}: {' → '.join(status_codes)}"]


def _then_source_facts(source: str) -> list[str]:
    """Extract compact observable assertions from exact Then binding source."""
    facts: list[str] = []
    ok = _RESULT_OK_RE.search(source)
    if ok is not None:
        facts.append(
            "public result succeeds" if ok.group(1) == "True" else "public result fails"
        )
    error_type = _ERROR_TYPE_RE.search(source)
    if error_type is not None:
        facts.append(error_type.group(1))
    request_count = _REQUEST_COUNT_RE.search(source)
    if request_count is not None:
        count = int(request_count.group(1))
        noun = "provider request" if count == 1 else "provider requests"
        facts.append(f"{count} {noun}")
    return facts


def _conditions_and_proof(steps: tuple[LivingStep, ...]) -> tuple[str, str]:
    """Derive scenario semantics plus a few objective source-level facts."""
    given: list[str] = []
    observed: list[str] = []
    given_sources: list[str] = []
    then_sources: list[str] = []
    phase = "given"
    for step in steps:
        keyword, text = _step_parts(step.name)
        source = step.implementation.source if step.implementation is not None else ""
        if keyword == "When":
            phase = "when"
            continue
        if keyword == "Then":
            phase = "then"
            observed.append(text)
            then_sources.append(source)
            continue
        if keyword in {"Given", "And", "But"}:
            if phase == "given":
                given.append(text)
                given_sources.append(source)
            elif phase == "then":
                observed.append(text)
                then_sources.append(source)

    injected = _append_facts(
        _compact_sentences(given),
        _given_source_facts("\n".join(given_sources)),
    )
    proof = _append_facts(
        _compact_sentences(observed),
        _then_source_facts("\n".join(then_sources)),
    )
    return injected, proof


def _implementation_text(steps: tuple[LivingStep, ...]) -> str:
    """Return only exact bindings captured for this scenario."""
    return "\n".join(
        step.implementation.source
        for step in steps
        if step.implementation is not None and step.implementation.source
    )


def _when_source(steps: tuple[LivingStep, ...]) -> str:
    """Return captured source for the executed When binding."""
    step = next(
        (
            item
            for item in steps
            if _step_parts(item.name)[0] == "When" and item.implementation is not None
        ),
        None,
    )
    return (
        step.implementation.source if step is not None and step.implementation else ""
    )


def _call_function_name(node: ast.AST) -> str:
    """Return the final callable name for one AST call node."""
    if not isinstance(node, ast.Call):
        return ""
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def _call_label(name: str) -> str:
    """Return a useful public/worker label for one callable name."""
    ignored = {
        "ScriptedHTTPServer",
        "request_count",
        "len",
        "isinstance",
        "str",
        "int",
        "bool",
    }
    if not name or name in ignored:
        return ""
    if name in {"query", "query_async"}:
        return f"LLMRouter.{name}"
    return name if name.startswith("run_") and name.endswith("_worker") else ""


def _when_call_label(steps: tuple[LivingStep, ...]) -> str:
    """Extract the main executable call from the captured When binding."""
    source = _when_source(steps)
    if not source:
        return ""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ""
    candidates = tuple(
        label
        for node in ast.walk(tree)
        if (label := _call_label(_call_function_name(node)))
    )
    public = next((label for label in candidates if label.startswith("LLMRouter.")), "")
    return public or (candidates[0] if candidates else "")


def _fallback_boundary_kind(tags: tuple[str, ...], captured: str) -> str:
    """Classify source/tag fallback only when runtime evidence is unavailable."""
    normalized_tags = {tag.casefold() for tag in tags}
    kind = "direct"
    if _SCRIPTED_HTTP in captured:
        kind = "scripted-http"
    elif "vcr" in normalized_tags:
        kind = "vcr"
    elif _TMP_PATH in captured or "TemporaryDirectory" in captured:
        kind = "temporary-filesystem"
    elif "monkeypatch" in captured:
        kind = "patched-runtime"
    elif "hermetic" in normalized_tags:
        kind = "hermetic"
    return kind


def _boundary_details(kind: str) -> tuple[str, str, str, str]:
    """Return path suffix, real scope, substitute, and excluded scope."""
    if kind == "scripted-http":
        return (
            "production code → HTTP client ┃ scripted HTTP server",
            (
                "Production application/provider code and the real HTTP client "
                "execute up to the outbound HTTP boundary."
            ),
            (
                "The external provider/service is replaced by a local "
                "ScriptedHTTPServer with deterministic provider-shaped responses."
            ),
            (
                "Live provider infrastructure, Internet/TLS/DNS behavior, real "
                "remote authentication, and vendor-side behavior."
            ),
        )
    if kind == "vcr":
        return (
            "production code → HTTP client ┃ recorded HTTP replay",
            (
                "Production code executes through the real HTTP client and "
                "provider integration path."
            ),
            (
                "The external HTTP interaction is replayed from retained VCR "
                "traffic instead of contacting the live provider during this run."
            ),
            (
                "Current live-provider availability and remote behavior that "
                "changed since the retained interaction was recorded."
            ),
        )
    if kind == "temporary-filesystem":
        return (
            "production code → filesystem ┃ temporary test path",
            (
                "Production persistence code executes against the real local "
                "filesystem API."
            ),
            "Persistent user storage is replaced by an isolated temporary path.",
            (
                "Long-lived storage, cross-process access, and host-specific "
                "filesystem behavior."
            ),
        )
    if kind == "patched-runtime":
        return (
            "production code ┃ patched runtime dependency",
            (
                "The production code path invoked by the BDD binding executes "
                "in-process."
            ),
            (
                "Selected environment/runtime dependencies are patched by the "
                "test harness."
            ),
            "Behavior of the patched external/runtime dependency itself.",
        )
    if kind == "hermetic":
        return (
            "production code ┃ hermetic local resources",
            (
                "The production code path invoked by the BDD binding executes "
                "in-process."
            ),
            (
                "External dependencies are excluded in favor of hermetic local "
                "test resources."
            ),
            (
                "External-system behavior outside the explicitly exercised local "
                "boundary."
            ),
        )
    return (
        "production code",
        "The production code path invoked by the BDD binding executes directly.",
        ("No explicit test substitute is visible in the captured BDD bindings."),
        "Behavior outside the explicitly exercised and asserted scenario path.",
    )


def _boundary_details_for(
    kind: str,
    facts: RuntimeAssuranceFacts | None,
) -> tuple[str, str, str, str]:
    """Prefer captured assurance detail and otherwise use the generic fallback."""
    captured = _captured_boundary_details(kind, facts)
    return captured if captured is not None else _boundary_details(kind)


def infer_boundary(
    *,
    tags: tuple[str, ...],
    steps: tuple[LivingStep, ...],
    runtime: VerificationRuntimeEvidence | None = None,
    coverage: CoverageFootprint | None = None,
) -> LivingVerificationBoundary | None:
    """Infer a conservative, human-readable verification boundary."""
    if not steps:
        return None

    captured = _implementation_text(steps)
    facts = runtime_assurance_facts(runtime, coverage)
    kind = facts.mechanism if facts else _fallback_boundary_kind(tags, captured)
    injected, observed = _conditions_and_proof(steps)
    entry = _when_call_label(steps)
    path, real_path, substitute, not_covered = _boundary_details_for(kind, facts)
    process, network, filesystem, external, provenance = _runtime_labels(facts)
    prefix = f"{entry} → " if entry else ""
    return LivingVerificationBoundary(
        path=f"{prefix}{_observed_path(path, facts)}",
        real_path=real_path,
        substitute=substitute,
        injected_condition=injected,
        observed_proof=observed,
        not_covered=not_covered,
        process=process,
        network=network,
        filesystem=filesystem,
        external=external,
        provenance=provenance,
        interactions=facts.interactions if facts is not None else (),
    )
