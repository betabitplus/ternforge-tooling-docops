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
from ternforge_docops._internal.documentation import (
    build_dossier as build_dossier,
    build_html as build_html,
    build_portal as build_portal,
)
from ternforge_docops._internal.experiments import (
    capture_experiment as capture_experiment,
    discover_capsules as discover_capsules,
    resolve_capsule as resolve_capsule,
    validate_experiments as validate_experiments,
)
from ternforge_docops._internal.resources import (
    graph_config_path as graph_config_path,
    stale_resources as stale_resources,
    static_dir_path as static_dir_path,
    sync_resources as sync_resources,
)
from ternforge_docops._internal.sphinx import (
    configure_experiment_mounts as configure_experiment_mounts,
    publish_experiment_inputs as publish_experiment_inputs,
    register_verification_view as register_verification_view,
)

DocOpsConfig = _Config
