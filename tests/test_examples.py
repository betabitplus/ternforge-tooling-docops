"""Offline contract checks for live examples."""

from __future__ import annotations

import importlib
import socket
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples" / "ternforge_docops"


def _example_modules() -> list[str]:
    return [
        f"examples.ternforge_docops.{path.stem}"
        for path in sorted(EXAMPLES_DIR.glob("*.py"))
        if path.name != "__init__.py"
    ]


@pytest.mark.hermetic
def test_examples_import_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Examples remain importable without starting live workflows."""

    def block_network(*_args: object, **_kwargs: object) -> None:
        msg = "example import attempted network access"
        raise AssertionError(msg)

    monkeypatch.setattr(socket.socket, "connect", block_network)
    monkeypatch.setattr(socket, "create_connection", block_network)

    modules = _example_modules()
    assert modules
    for module in modules:
        importlib.import_module(module)
