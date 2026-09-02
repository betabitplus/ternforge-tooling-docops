"""Public configuration
====================

Install and read the public configuration snapshot for ternforge docops.
"""
# sphinx_gallery_tags = ["configuration", "public-api"]

# %%
from __future__ import annotations

from ternforge_docops import (
    DocOpsConfig,
    get_config,
    install_config,
)


def main() -> None:
    """Install and read the public config snapshot."""
    config = install_config(DocOpsConfig())
    active_config = get_config()
    print(f"active_config: {type(active_config).__name__}")
    print(f"same_object: {active_config is config}")


# %%
if __name__ == "__main__":
    main()
