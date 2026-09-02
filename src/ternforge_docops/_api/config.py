"""Public config re-exports.

Why:
    Keeps config names behind the `_api` facade while `_internal` owns config
    models, validation, runtime default assembly, and snapshot state.
"""

from __future__ import annotations

# pyright: reportUnusedImport=false
from ternforge_docops._internal import (  # noqa: F401
    DocOpsConfig,
    get_config,
    install_config,
)
