"""Coverage.py dynamic-context evidence for per-test production execution."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CoverageFile:
    """One production source file executed by one pytest nodeid."""

    path: str
    lines: tuple[int, ...]
    phases: tuple[str, ...]


@dataclass(frozen=True)
class CoverageFootprint:
    """Per-test production coverage recovered from pytest-cov contexts."""

    nodeid: str
    files: tuple[CoverageFile, ...]

    @property
    def primary_files(self) -> tuple[CoverageFile, ...]:
        """Return production files ordered by amount of executed code."""
        return tuple(
            sorted(
                self.files,
                key=lambda item: (-len(item.lines), item.path),
            )
        )


def _production_module(path: str) -> str:
    """Normalize one covered source path into a compact production-module name."""
    if not path.startswith("src/"):
        return ""
    value = path.removeprefix("src/").removesuffix(".py")
    parts = [part for part in value.split("/") if part and part != "_internal"]
    package_relative = parts[1:] if len(parts) > 1 else parts
    return ".".join(package_relative) or path


def production_modules(
    footprint: CoverageFootprint | None,
    *,
    limit: int = 3,
) -> tuple[str, ...]:
    """Return compact production-module names observed in one test context."""
    if footprint is None or limit <= 0:
        return ()
    modules = tuple(
        dict.fromkeys(
            module
            for file in footprint.primary_files
            if (module := _production_module(file.path))
        )
    )
    return modules[:limit]


def _context_identity(value: str) -> tuple[str, str]:
    """Split pytest-cov dynamic context into nodeid and execution phase."""
    nodeid, separator, phase = value.rpartition("|")
    if not separator:
        return value, ""
    return nodeid, phase


def _read_coverage_files(coverage: Path | None) -> dict[str, Any]:
    """Return the coverage.py files mapping when a valid report exists."""
    if coverage is None or not coverage.is_file():
        return {}
    try:
        data = json.loads(coverage.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    raw_files = data.get("files") if isinstance(data, dict) else None
    return raw_files if isinstance(raw_files, dict) else {}


def _normalized_contexts(
    raw_line: object,
    raw_contexts: object,
) -> tuple[int, tuple[tuple[str, str], ...]] | None:
    """Normalize one coverage line and its pytest dynamic contexts."""
    if not isinstance(raw_contexts, list):
        return None
    try:
        line = int(raw_line)
    except (TypeError, ValueError):
        return None
    identities = tuple(
        identity
        for raw_context in raw_contexts
        if isinstance(raw_context, str) and raw_context
        if (identity := _context_identity(raw_context))[0]
    )
    return line, identities


def _record_contexts(
    *,
    path: str,
    contexts: dict[str, Any],
    lines_by_test: dict[str, dict[str, set[int]]],
    phases_by_test: dict[str, dict[str, set[str]]],
) -> None:
    """Collect one coverage.py file's dynamic contexts by pytest nodeid."""
    for raw_line, raw_contexts in contexts.items():
        normalized = _normalized_contexts(raw_line, raw_contexts)
        if normalized is None:
            continue
        line, identities = normalized
        for nodeid, phase in identities:
            lines_by_test[nodeid][path].add(line)
            if phase:
                phases_by_test[nodeid][path].add(phase)


def load_coverage_footprints(
    coverage: Path | None,
) -> dict[str, CoverageFootprint]:
    """Load per-test executed production files from coverage.py JSON contexts."""
    raw_files = _read_coverage_files(coverage)
    lines_by_test: dict[str, dict[str, set[int]]] = defaultdict(
        lambda: defaultdict(set)
    )
    phases_by_test: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    for raw_path, raw_file in raw_files.items():
        if not isinstance(raw_file, dict):
            continue
        contexts = raw_file.get("contexts")
        if isinstance(contexts, dict):
            _record_contexts(
                path=raw_path,
                contexts=contexts,
                lines_by_test=lines_by_test,
                phases_by_test=phases_by_test,
            )

    return {
        nodeid: CoverageFootprint(
            nodeid=nodeid,
            files=tuple(
                CoverageFile(
                    path=path,
                    lines=tuple(sorted(lines)),
                    phases=tuple(sorted(phases_by_test[nodeid][path])),
                )
                for path, lines in files.items()
            ),
        )
        for nodeid, files in lines_by_test.items()
    }
