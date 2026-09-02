"""Tests for package-owned DocOps resources."""

from __future__ import annotations

from pathlib import Path

from ternforge_docops._internal.resources import stale_resources, sync_resources


def test_sync_resources_round_trip(tmp_path: Path) -> None:
    """Materialized resources are complete and detect later drift."""
    written = sync_resources(tmp_path)

    assert {path.name for path in written} == {"engineering.toml", "schemas.json"}
    assert stale_resources(tmp_path) == ()

    written[0].write_text("stale\n", encoding="utf-8")

    assert stale_resources(tmp_path) == (written[0],)
