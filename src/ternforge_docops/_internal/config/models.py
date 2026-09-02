"""Runtime configuration models for ternforge docops.

Why:
    Defines immutable config snapshots consumed by private runtime code.
"""

from __future__ import annotations

from dataclasses import dataclass

from ternforge_docops._internal.config.validation import (
    validate_config,
)


@dataclass(frozen=True, slots=True)
class DocOpsConfig:
    """Owns the validated runtime configuration.

    Add public config fields here when real runtime behavior needs them.
    """

    def __post_init__(self) -> None:
        """Validate the config snapshot at construction time."""
        validate_config(self)
