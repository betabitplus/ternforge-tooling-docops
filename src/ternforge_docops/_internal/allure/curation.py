"""Allure result curation from adapter-owned trace labels and the Needs graph."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import cast


def requirement_titles(needs_json: Path) -> dict[str, str]:
    """Return Need titles from one Sphinx-Needs JSON export."""
    data = json.loads(needs_json.read_text(encoding="utf-8"))
    current_version = str(data["current_version"])
    needs = data["versions"][current_version]["needs"]
    return {
        str(need_id): str(need.get("title") or need_id)
        for need_id, need in needs.items()
        if isinstance(need, dict)
    }


def _labels(result: dict[str, object]) -> list[dict[str, object]]:
    labels = result.get("labels")
    if isinstance(labels, list) and all(isinstance(label, dict) for label in labels):
        return cast("list[dict[str, object]]", labels)
    labels = []
    result["labels"] = labels
    return labels


def _label_values(result: dict[str, object], name: str) -> tuple[str, ...]:
    return tuple(
        str(label["value"])
        for label in _labels(result)
        if label.get("name") == name and "value" in label
    )


def _add_label(result: dict[str, object], name: str, value: str) -> None:
    labels = _labels(result)
    label = {"name": name, "value": value}
    if label not in labels:
        labels.append(label)


def _attachment_sources(result: dict[str, object]) -> set[str]:
    sources: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, list):
            for item in value:
                visit(item)
            return
        if not isinstance(value, dict):
            return
        attachments = value.get("attachments")
        if isinstance(attachments, list):
            for attachment in attachments:
                if isinstance(attachment, dict) and attachment.get("source"):
                    sources.add(str(attachment["source"]))
        steps = value.get("steps")
        if isinstance(steps, list):
            visit(steps)

    visit(result)
    return sources


def _copy_result(
    result_path: Path,
    result: dict[str, object],
    *,
    raw_results: Path,
    destination: Path,
) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    (destination / result_path.name).write_text(
        json.dumps(result, ensure_ascii=False),
        encoding="utf-8",
    )
    for source in _attachment_sources(result):
        attachment = raw_results / source
        if attachment.is_file():
            shutil.copy2(attachment, destination / source)


def curate_results(
    raw_results: Path,
    *,
    needs_json: Path,
    curated_results: Path,
    bdd_results: Path,
) -> None:
    """Create fixture-free Allure result sets with graph-backed presentation labels."""
    titles = requirement_titles(needs_json)
    for directory in (curated_results, bdd_results):
        shutil.rmtree(directory, ignore_errors=True)
        directory.mkdir(parents=True)

    for result_path in sorted(raw_results.glob("*-result.json")):
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if not isinstance(result, dict):
            continue
        for requirement_id in _label_values(result, "requirement"):
            title = titles.get(requirement_id, requirement_id)
            _add_label(
                result,
                "requirement_view",
                f"{requirement_id} — {title}",
            )
        _copy_result(
            result_path,
            result,
            raw_results=raw_results,
            destination=curated_results,
        )
        if "bdd" in _label_values(result, "layer"):
            _copy_result(
                result_path,
                result,
                raw_results=raw_results,
                destination=bdd_results,
            )
