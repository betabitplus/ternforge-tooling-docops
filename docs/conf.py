"""Sphinx configuration for ternforge-docops documentation."""

from __future__ import annotations

import os

project = "ternforge-docops"
extensions = ["ternforge_docops._api.sphinx_python"]
root_doc = "index"
exclude_patterns = ["_build", "README.md"]

# Required CI stays offline; live docs explicitly opt into external inventories.
intersphinx_mapping = {}
if os.getenv("SPHINX_ENABLE_INTERSPHINX") == "1":
    intersphinx_mapping = {
        "python": ("https://docs.python.org/3/", None),
    }
