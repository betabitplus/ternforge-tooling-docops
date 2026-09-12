"""Tests for structured runtime verification evidence ingestion."""

from __future__ import annotations

import json
from pathlib import Path

from ternforge_docops._internal.verification.coverage_evidence import (
    load_coverage_footprints,
)
from ternforge_docops._internal.verification.evidence import (
    inferred_nodeid,
    load_runtime_evidence,
    resolve_runtime_evidence,
)


def test_load_runtime_evidence_groups_observations_by_pytest_nodeid(
    tmp_path: Path,
) -> None:
    """All observations in one Allure result inherit its execution nodeid."""
    execution_source = tmp_path / "execution-attachment.json"
    execution_source.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "test-execution",
                "payload": {
                    "nodeid": "tests/pkg/test_adapter.py::test_boundary",
                    "path": "tests/pkg/test_adapter.py",
                    "verification_kind": "integration",
                    "fixtures": ["tmp_path"],
                    "markers": ["hermetic"],
                },
            }
        ),
        encoding="utf-8",
    )
    substitute_source = tmp_path / "substitute-attachment.json"
    substitute_source.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "external-substitute",
                "payload": {
                    "producer": "ScriptedHTTPServer",
                    "boundary": "provider-http",
                },
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "result-result.json").write_text(
        json.dumps(
            {
                "uuid": "result",
                "name": "test_boundary",
                "fullName": "tests.pkg.test_adapter#test_boundary",
                "start": 1,
                "stop": 2,
                "attachments": [
                    {
                        "name": "Ternforge test execution",
                        "type": (
                            "application/vnd.ternforge.verification-observation+json"
                        ),
                        "source": execution_source.name,
                    },
                    {
                        "name": "Provider boundary",
                        "type": (
                            "application/vnd.ternforge.verification-observation+json"
                        ),
                        "source": substitute_source.name,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    evidence = load_runtime_evidence(tmp_path)

    item = evidence["tests/pkg/test_adapter.py::test_boundary"]
    assert item.fixtures == ("tmp_path",)
    assert item.markers == ("hermetic",)
    assert item.source_path == "tests/pkg/test_adapter.py"
    assert [observation.kind for observation in item.observations] == [
        "test-execution",
        "external-substitute",
    ]
    assert (
        resolve_runtime_evidence(
            evidence,
            classname="tests.pkg.test_adapter",
            name="test_boundary",
        )
        == item
    )


def test_load_coverage_footprints_preserves_per_test_runtime_context(
    tmp_path: Path,
) -> None:
    """coverage.py contexts identify actual production files executed by each test."""
    coverage = tmp_path / "coverage.json"
    coverage.write_text(
        json.dumps(
            {
                "files": {
                    "src/pkg/adapter.py": {
                        "contexts": {
                            "10": [
                                "tests/pkg/test_adapter.py::test_boundary|run",
                            ],
                            "11": [
                                "tests/pkg/test_adapter.py::test_boundary|run",
                                "tests/pkg/test_adapter.py::test_error|run",
                            ],
                        }
                    },
                    "src/pkg/retry.py": {
                        "contexts": {
                            "20": [
                                "tests/pkg/test_adapter.py::test_boundary|setup",
                            ]
                        }
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    footprints = load_coverage_footprints(coverage)

    item = footprints["tests/pkg/test_adapter.py::test_boundary"]
    assert [file.path for file in item.primary_files] == [
        "src/pkg/adapter.py",
        "src/pkg/retry.py",
    ]
    assert item.primary_files[0].lines == (10, 11)
    assert item.primary_files[0].phases == ("run",)
    assert item.primary_files[1].phases == ("setup",)
    assert (
        inferred_nodeid(
            "tests.pkg.test_adapter",
            "test_boundary",
        )
        == "tests/pkg/test_adapter.py::test_boundary"
    )
