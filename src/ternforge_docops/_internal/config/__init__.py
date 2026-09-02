"""Runtime configuration package for ternforge docops.

Why:
    Owns validated immutable configuration snapshots for private runtime
    instances.
"""

from __future__ import annotations

from ternforge_docops._internal.config.assembly import (
    build_default_config as build_default_config,
)
from ternforge_docops._internal.config.models import (
    DocOpsConfig as _Config,
)
from ternforge_docops._internal.config.state import (
    get_config as get_config,
    install_config as install_config,
)
from ternforge_docops._internal.config.validation import (
    validate_config as validate_config,
)

DocOpsConfig = _Config
