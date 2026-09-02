"""Private implementation root for ternforge docops.

Why:
    Provides narrow private-root entrypoints used by `_api` facades so facade
    modules do not import deep implementation modules.
"""

from __future__ import annotations

from ternforge_docops._internal.config import (
    DocOpsConfig as _Config,
    get_config as get_config,
    install_config as install_config,
)
from ternforge_docops._internal.resources import (
    graph_config_path as graph_config_path,
    stale_resources as stale_resources,
    sync_resources as sync_resources,
)

DocOpsConfig = _Config
