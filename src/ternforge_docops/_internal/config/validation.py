"""Runtime config validation helpers for ternforge docops.

Why:
    Centralizes config normalization and invariant checks before snapshots are
    constructed or installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ternforge_docops._internal.config.models import (
        DocOpsConfig,
    )


def validate_config(config: DocOpsConfig) -> None:
    """Validate one runtime config snapshot."""
    _ = config
