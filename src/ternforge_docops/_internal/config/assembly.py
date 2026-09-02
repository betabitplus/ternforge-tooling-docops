"""Built-in config assembly for ternforge docops.

Why:
    Converts public default declarations into validated private config
    snapshots before runtime work begins.
"""

from __future__ import annotations

from ternforge_docops._internal.config.models import (
    DocOpsConfig,
)
from ternforge_docops._internal.config.validation import (
    validate_config,
)


def build_default_config() -> DocOpsConfig:
    """Assemble and validate the built-in runtime config snapshot."""
    config = DocOpsConfig()
    validate_config(config)
    return config
