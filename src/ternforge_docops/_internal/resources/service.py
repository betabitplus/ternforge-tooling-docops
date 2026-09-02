"""Package-owned resources materialized for repository authoring tools."""

from __future__ import annotations

from pathlib import Path

_RESOURCE_ROOT = Path(__file__).resolve().parent / "graph"
_RESOURCE_NAMES = ("engineering.toml", "schemas.json")
_TARGET_DIR = Path(".ternforge") / "docops"


def graph_config_path() -> Path:
    """Return the canonical Sphinx-Needs graph configuration path."""
    return _RESOURCE_ROOT / "engineering.toml"


def sync_resources(root: Path) -> tuple[Path, ...]:
    """Materialize canonical DocOps resources under a repository root."""
    target_root = root.resolve() / _TARGET_DIR
    target_root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name in _RESOURCE_NAMES:
        source = _RESOURCE_ROOT / name
        target = target_root / name
        target.write_bytes(source.read_bytes())
        written.append(target)
    return tuple(written)


def stale_resources(root: Path) -> tuple[Path, ...]:
    """Return missing or stale materialized resource paths."""
    target_root = root.resolve() / _TARGET_DIR
    stale: list[Path] = []
    for name in _RESOURCE_NAMES:
        source = _RESOURCE_ROOT / name
        target = target_root / name
        if not target.is_file() or target.read_bytes() != source.read_bytes():
            stale.append(target)
    return tuple(stale)
