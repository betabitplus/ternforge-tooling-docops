"""Human-readable narrative pages for non-BDD verification evidence."""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from defusedxml.ElementTree import parse as parse_xml

from ternforge_docops._internal.verification.assurance import VerificationBoundary
from ternforge_docops._internal.verification.case_boundary import (
    CaseBoundaryInput,
    infer_case_boundary,
)
from ternforge_docops._internal.verification.coverage_evidence import (
    CoverageFootprint,
    load_coverage_footprints,
)
from ternforge_docops._internal.verification.evidence import (
    VerificationRuntimeEvidence,
    inferred_nodeid,
    load_runtime_evidence,
    resolve_runtime_evidence,
)
from ternforge_docops._internal.verification.source_analysis import (
    extract_checks,
    extract_exercises,
    extract_generated_inputs,
    human_words,
    module_title,
)

_SUPPORTED_KINDS = frozenset({"unit", "property", "integration", "e2e"})
_TEST_PREFIX = "test_"
_TICK = chr(96)


class _JUnitElement(Protocol):
    """Subset of Element API consumed from the defused JUnit parser."""

    def get(self, key: str, default: str | None = None) -> str | None:
        """Return one XML attribute value."""
        ...

    def findall(self, path: str) -> Iterable[_JUnitElement]:
        """Return child elements matching one XML path."""
        ...


@dataclass(frozen=True)
class VerificationNarrativePage:
    """One generated verification document."""

    docname: str
    source: str


@dataclass(frozen=True)
class _Case:
    """One non-BDD testcase enriched from its Python source."""

    kind: str
    classname: str
    name: str
    verifies: str
    source_path: str
    line_start: int | None
    line_end: int | None
    code: str
    exercises: tuple[str, ...]
    checks: tuple[str, ...]
    generated_inputs: tuple[str, ...]
    runtime: VerificationRuntimeEvidence | None
    coverage: CoverageFootprint | None
    boundary: VerificationBoundary | None


@dataclass(frozen=True)
class _CaseRequest:
    """JUnit identity plus structured evidence for one narrative case."""

    kind: str
    classname: str
    name: str
    verifies: str
    runtime: VerificationRuntimeEvidence | None
    coverage: CoverageFootprint | None


def _slug(value: str) -> str:
    """Create a stable Sphinx-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug or "verification"


def verification_docname(kind: str, classname: str) -> str:
    """Return the generated document name for one verification source module."""
    return f"verification/_generated/{_slug(kind)}/{_slug(classname)}"


def verification_anchor(kind: str, classname: str, name: str) -> str:
    """Return the stable anchor for one concrete testcase."""
    return f"verification-{_slug(kind)}-{_slug(classname)}-{_slug(name)}"


def _title(name: str) -> str:
    """Humanize one pytest testcase name."""
    base = name
    parameter = ""
    if "[" in base and base.endswith("]"):
        base, parameter = base[:-1].split("[", 1)
    base = base.removeprefix(_TEST_PREFIX)
    text = human_words(base)
    if parameter:
        return f"{text} — {parameter.replace('_', ' ')}"
    return text


def _properties(testcase: _JUnitElement) -> dict[str, str]:
    """Return JUnit testcase properties."""
    return {
        str(prop.get("name")): str(prop.get("value") or "")
        for prop in testcase.findall("./properties/property")
        if prop.get("name")
    }


def _source_path(root: Path, classname: str) -> Path | None:
    """Resolve a pytest classname to a repository Python source file."""
    candidate = root.joinpath(*classname.split(".")).with_suffix(".py")
    return candidate if candidate.is_file() else None


def _empty_case(request: _CaseRequest, source_path: str = "") -> _Case:
    """Return one narrative record when source enrichment is unavailable."""
    return _Case(
        kind=request.kind,
        classname=request.classname,
        name=request.name,
        verifies=request.verifies,
        source_path=source_path,
        line_start=None,
        line_end=None,
        code="",
        exercises=(),
        checks=(),
        generated_inputs=(),
        runtime=request.runtime,
        coverage=request.coverage,
        boundary=None,
    )


def _function_case(root: Path, request: _CaseRequest) -> _Case:
    """Build one testcase narrative from structured evidence plus source fallback."""
    path = _source_path(root, request.classname)
    if path is None:
        return _empty_case(request)

    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    function_name = request.name.split("[", 1)[0]
    function = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == function_name
        ),
        None,
    )
    source_path = path.relative_to(root).as_posix()
    if function is None:
        return _empty_case(request, source_path)

    code = ast.get_source_segment(source, function) or ""
    exercises = extract_exercises(function)
    checks = extract_checks(function)
    generated_inputs = extract_generated_inputs(function)
    boundary_input = CaseBoundaryInput(
        kind=request.kind,
        source_path=source_path,
        code=code,
        exercises=exercises,
        checks=checks,
        generated_inputs=generated_inputs,
        runtime=request.runtime,
        coverage=request.coverage,
    )
    return _Case(
        kind=request.kind,
        classname=request.classname,
        name=request.name,
        verifies=request.verifies,
        source_path=source_path,
        line_start=function.lineno,
        line_end=getattr(function, "end_lineno", None),
        code=code,
        exercises=exercises,
        checks=checks,
        generated_inputs=generated_inputs,
        runtime=request.runtime,
        coverage=request.coverage,
        boundary=infer_case_boundary(boundary_input),
    )


def _case_request(
    testcase: _JUnitElement,
    *,
    runtime_evidence: dict[str, VerificationRuntimeEvidence],
    coverage_footprints: dict[str, CoverageFootprint],
) -> _CaseRequest | None:
    """Resolve one JUnit testcase against structured runtime evidence."""
    props = _properties(testcase)
    kind = props.get("verification_kind", "")
    if kind not in _SUPPORTED_KINDS:
        return None
    classname = str(testcase.get("classname") or "")
    name = str(testcase.get("name") or "")
    if not classname or not name:
        return None
    runtime = resolve_runtime_evidence(
        runtime_evidence,
        classname=classname,
        name=name,
    )
    nodeid = runtime.nodeid if runtime is not None else inferred_nodeid(classname, name)
    return _CaseRequest(
        kind=kind,
        classname=classname,
        name=name,
        verifies=props.get("verifies", ""),
        runtime=runtime,
        coverage=coverage_footprints.get(nodeid),
    )


def _cases(
    root: Path,
    junit: Path,
    *,
    runtime_evidence: dict[str, VerificationRuntimeEvidence],
    coverage_footprints: dict[str, CoverageFootprint],
) -> list[_Case]:
    """Load current non-BDD verification evidence from retained artifacts."""
    tree = parse_xml(junit)
    requests = (
        request
        for testcase in tree.getroot().iter("testcase")
        if (
            request := _case_request(
                testcase,
                runtime_evidence=runtime_evidence,
                coverage_footprints=coverage_footprints,
            )
        )
        is not None
    )
    return [_function_case(root, request) for request in requests]


def _method_sentence(case: _Case) -> str:
    """Describe the verification method without status or execution trivia."""
    if case.kind == "unit":
        return (
            "Exercises focused logic directly and checks the observable values or "
            "errors that define this contract."
        )
    if case.kind == "integration":
        return (
            "Exercises the component through a controlled integration boundary and "
            "checks the data or errors observed across that boundary."
        )
    if case.kind == "property":
        return (
            "Generates many inputs from the declared strategies and checks that the "
            "same invariant holds for every generated example."
        )
    return (
        "Exercises the public workflow end to end and checks the resulting observable "
        "behavior."
    )


def _literal(value: str) -> str:
    """Render one compact RST inline literal."""
    return f"{_TICK}{_TICK}{value.replace(_TICK, '')}{_TICK}{_TICK}"


def _need_role(target: str) -> str:
    """Render one Sphinx-Needs reference without hard-coding markup punctuation."""
    return f":need:{_TICK}{target}{_TICK}"


def _code_block(lines: list[str], code: str, indent: int = 3) -> None:
    """Append one Python code block."""
    prefix = " " * indent
    lines.append(f"{prefix}.. code-block:: python")
    lines.append("")
    lines.extend(f"{prefix}   {line}" for line in code.splitlines())
    lines.append("")


def _list(lines: list[str], values: tuple[str, ...], indent: int) -> None:
    """Render compact literal bullets."""
    prefix = " " * indent
    if not values:
        lines.append(f"{prefix}No additional detail is needed beyond the test body.")
        lines.append("")
        return
    lines.extend(f"{prefix}* {_literal(value)}" for value in values)
    lines.append("")


def _render_boundary(lines: list[str], boundary: VerificationBoundary) -> None:
    """Render the verification scope before exercise/assertion details."""
    lines.extend(
        (
            ".. card:: Verification boundary",
            "",
            f"   **Path:** {_literal(boundary.path)}",
            "",
            (
                "   **Execution envelope:** "
                f":bdg-secondary:{_TICK}Process · {boundary.process}{_TICK} "
                f":bdg-secondary:{_TICK}Network · {boundary.network}{_TICK} "
                f":bdg-secondary:{_TICK}Filesystem · {boundary.filesystem}{_TICK} "
                f":bdg-secondary:{_TICK}External · {boundary.external}{_TICK}"
            ),
            "",
            f"   * **Real path:** {boundary.real_path}",
            f"   * **Substitute:** {boundary.substitute}",
            f"   * **Not covered:** {boundary.not_covered}",
            "",
            "   .. dropdown:: How this verification establishes the proof",
            "",
            f"      **Observed proof:** {_literal(boundary.observed_proof)}",
            "",
            f"      **Boundary basis:** {boundary.provenance}",
            "",
        )
    )


def _render_case(case: _Case) -> str:
    """Render one testcase as progressive narrative RST."""
    anchor = verification_anchor(case.kind, case.classname, case.name)
    title = _title(case.name)
    lines = [f".. _{anchor}:", "", title, "-" * len(title), ""]
    target = case.verifies.split("[", 1)[0].strip()
    if target:
        lines.extend((f"**Verifies:** {_need_role(target)}", ""))
    lines.extend((_method_sentence(case), ""))
    if case.boundary is not None:
        _render_boundary(lines, case.boundary)

    if case.kind == "property" and case.generated_inputs:
        lines.extend(
            (
                ".. grid:: 1 2 2 2",
                "   :gutter: 2",
                "",
                "   .. grid-item-card:: Generated inputs",
                "",
            )
        )
        _list(lines, case.generated_inputs, 6)
        lines.extend(("   .. grid-item-card:: Invariant", ""))
        _list(lines, case.checks, 6)
    else:
        lines.extend(
            (
                ".. grid:: 1 2 2 2",
                "   :gutter: 2",
                "",
                "   .. grid-item-card:: Exercise",
                "",
            )
        )
        _list(lines, case.exercises, 6)
        lines.extend(("   .. grid-item-card:: Checks", ""))
        _list(lines, case.checks, 6)

    if case.code:
        location = case.source_path
        if case.line_start is not None:
            location = f"{location}:{case.line_start}"
            if case.line_end is not None and case.line_end != case.line_start:
                location = f"{location}-{case.line_end}"
        lines.extend((".. dropdown:: Test code", "", f"   {_literal(location)}", ""))
        _code_block(lines, case.code, 3)
    return "\n".join(lines).rstrip() + "\n"


def _render_page(
    kind: str,
    classname: str,
    cases: list[_Case],
) -> VerificationNarrativePage:
    """Render one module-level verification narrative page."""
    cases = sorted(
        cases,
        key=lambda case: (
            case.line_start if case.line_start is not None else 10**9,
            case.name,
        ),
    )
    first = cases[0]
    title = module_title(first.source_path or classname)
    kind_title = {
        "unit": "Unit verification",
        "integration": "Integration verification",
        "property": "Property verification",
        "e2e": "End-to-end verification",
    }[kind]
    lines = [
        ":orphan:",
        "",
        f":doc:{_TICK}← Traceability reader </traceability-reader>{_TICK}",
        "",
        title,
        "=" * len(title),
        "",
        f":bdg-secondary:{_TICK}{kind_title}{_TICK}",
        "",
        (
            "What is exercised, where test substitutes begin, what observations "
            "establish the contract, and where this verification stops. Source code "
            "stays one level deeper for inspection when needed."
        ),
        "",
    ]
    lines.extend(_render_case(case) for case in cases)
    return VerificationNarrativePage(
        docname=verification_docname(kind, classname),
        source="\n".join(lines).rstrip() + "\n",
    )


def render_verification_narratives(
    root: Path,
    junit: Path | None,
    *,
    allure_results: Path | None = None,
    coverage: Path | None = None,
) -> tuple[VerificationNarrativePage, ...]:
    """Build narratives from JUnit plus captured runtime/coverage evidence."""
    if junit is None or not junit.is_file():
        return ()
    runtime_evidence = load_runtime_evidence(allure_results)
    coverage_footprints = load_coverage_footprints(coverage)
    grouped: dict[tuple[str, str], list[_Case]] = defaultdict(list)
    for case in _cases(
        root,
        junit,
        runtime_evidence=runtime_evidence,
        coverage_footprints=coverage_footprints,
    ):
        grouped[(case.kind, case.classname)].append(case)
    return tuple(
        _render_page(kind, classname, grouped[(kind, classname)])
        for kind, classname in sorted(grouped)
    )
