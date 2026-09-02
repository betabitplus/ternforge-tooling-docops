"""Runtime config snapshot state for ternforge docops.

Why:
    Keeps process-wide config construction and install/read helpers inside the
    private config implementation.
"""

from __future__ import annotations

from threading import RLock

from ternforge_docops._internal.config.assembly import (
    build_default_config,
)
from ternforge_docops._internal.config.models import (
    DocOpsConfig,
)
from ternforge_docops._internal.config.validation import (
    validate_config,
)

_installed_config: DocOpsConfig = build_default_config()
_config_lock = RLock()


def get_config(
    config: DocOpsConfig | None = None,
) -> DocOpsConfig:
    """Return a validated runtime configuration snapshot."""
    if config is not None:
        return config
    with _config_lock:
        return _installed_config


def install_config(config: object) -> DocOpsConfig:
    """Install a validated runtime configuration snapshot."""
    if not isinstance(config, DocOpsConfig):
        msg = f"install_config() expects a {DocOpsConfig.__name__} instance."
        raise TypeError(msg)

    validate_config(config)
    global _installed_config  # noqa: PLW0603
    with _config_lock:
        _installed_config = config

    return config
