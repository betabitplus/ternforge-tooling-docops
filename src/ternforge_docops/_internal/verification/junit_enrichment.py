"""Build-only enrichment of JUnit evidence with objective assurance facts."""

from __future__ import annotations

from pathlib import Path

from defusedxml.ElementTree import parse as parse_xml

from ternforge_docops._internal.verification.coverage_evidence import (
    load_coverage_footprints,
)
from ternforge_docops._internal.verification.evidence import (
    inferred_nodeid,
    load_runtime_evidence,
    resolve_runtime_evidence,
)
from ternforge_docops._internal.verification.producers import evidence_producer_ids
from ternforge_docops._internal.verification.scope import verification_scope


def _properties(testcase: object) -> dict[str, str]:
    """Read one JUnit testcase property mapping."""
    findall = testcase.findall
    values: dict[str, str] = {}
    for item in findall("./properties/property"):
        name = str(item.get("name") or "")
        value = str(item.get("value") or "")
        if name:
            values[name] = value
    return values


def _properties_node(testcase: object) -> object:
    """Return or create the JUnit properties element for one testcase."""
    find = testcase.find
    properties = find("properties")
    if properties is not None:
        return properties
    makeelement = testcase.makeelement
    properties = makeelement("properties", {})
    insert = testcase.insert
    insert(0, properties)
    return properties


def _set_property(testcase: object, name: str, value: str) -> None:
    """Replace one generated JUnit property deterministically."""
    properties = _properties_node(testcase)
    findall = properties.findall
    remove = properties.remove
    for item in list(findall("property")):
        if item.get("name") == name:
            remove(item)
    makeelement = properties.makeelement
    append = properties.append
    append(makeelement("property", {"name": name, "value": value}))


def enrich_junit_evidence(
    junit: Path,
    target: Path,
    *,
    allure_results: Path | None = None,
    coverage: Path | None = None,
) -> None:
    """Write a transient JUnit copy enriched from retained runtime/coverage facts."""
    tree = parse_xml(junit)
    runtime_evidence = load_runtime_evidence(allure_results)
    coverage_footprints = load_coverage_footprints(coverage)
    enriched = False

    for testcase in tree.getroot().iter("testcase"):
        classname = str(testcase.get("classname") or "")
        name = str(testcase.get("name") or "")
        if not classname or not name:
            continue
        props = _properties(testcase)
        runtime = resolve_runtime_evidence(
            runtime_evidence,
            classname=classname,
            name=name,
        )
        nodeid = (
            runtime.nodeid if runtime is not None else inferred_nodeid(classname, name)
        )
        scope = verification_scope(
            runtime,
            coverage_footprints.get(nodeid),
            gherkin_feature=props.get("gherkin_feature", ""),
        )
        producers = evidence_producer_ids(
            runtime,
            gherkin_feature=props.get("gherkin_feature", ""),
        )

        _set_property(testcase, "nodeid", nodeid)
        _set_property(testcase, "scope_reach", scope.reach)
        _set_property(testcase, "scope_basis", scope.basis)
        _set_property(testcase, "external_reach", scope.external_reach)
        if producers:
            _set_property(testcase, "produced_by", ",".join(producers))
        enriched = True

    target.parent.mkdir(parents=True, exist_ok=True)
    if not enriched:
        target.write_bytes(junit.read_bytes())
        return
    tree.write(target, encoding="utf-8", xml_declaration=True)
