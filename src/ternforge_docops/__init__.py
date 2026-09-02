"""Supported public package entrypoint for `ternforge_docops`.

Why:
    Exposes the stable public surface from one import boundary.

What belongs here:
    Re-exports of facade functions/classes, public DTOs, config objects,
    vocabulary types, public exceptions, and package version.

What does not belong here:
    Raw defaults, private runtime helpers, adapters, stores, or other
    implementation details.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from ternforge_docops._api.config import (
    DocOpsConfig,
    get_config,
    install_config,
)
from ternforge_docops._api.errors import (
    InvalidConfigValueError,
    TernforgeDocOpsError,
)

try:
    __version__ = version("ternforge-docops")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0+local"

__all__ = [
    "DocOpsConfig",
    "InvalidConfigValueError",
    "TernforgeDocOpsError",
    "__version__",
    "get_config",
    "install_config",
]
