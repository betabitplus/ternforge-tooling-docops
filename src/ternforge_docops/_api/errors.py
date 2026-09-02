"""Public exceptions for ternforge docops.

Why:
    Keeps caller-facing failure types separate from private runtime details.
"""

from __future__ import annotations


class TernforgeDocOpsError(Exception):
    """Base class for package-specific public errors."""


class InvalidConfigValueError(TernforgeDocOpsError, ValueError):
    """Raised when public config input violates a config invariant."""

    def __init__(self, *, field: str, value: object, reason: str) -> None:
        """Build a caller-safe config validation message."""
        self.field = field
        self.value = value
        self.reason = reason
        super().__init__(f"Invalid config value for {field}: {value!r} ({reason}).")
