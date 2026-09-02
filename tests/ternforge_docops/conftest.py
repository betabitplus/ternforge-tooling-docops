"""Package-specific pytest fixtures for ternforge docops."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from ternforge_docops import (
    DocOpsConfig,
    install_config,
)


@pytest.fixture(autouse=True)
def reset_installed_config() -> Iterator[None]:
    """Reset process-wide config around each package test."""
    install_config(DocOpsConfig())
    try:
        yield
    finally:
        install_config(DocOpsConfig())
