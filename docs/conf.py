"""Sphinx configuration for ternforge-docops documentation."""

from __future__ import annotations

import os
from pathlib import Path

project = "ternforge-docops"

extensions = [
    "ternforge_docops._api.sphinx",
    "sphinx_codelinks",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx_gallery.gen_gallery",
]

root_doc = "index"
src_trace_config_from_toml = "../ubproject.toml"
exclude_patterns = ["_build", "README.md"]
myst_fence_as_directive = {"mermaid"}
html_theme = "pydata_sphinx_theme"
simplepdf_file_name = "release-dossier.pdf"

local_pytest_junit = Path(__file__).parent / "_traceability" / "local-pytest.xml"
if not local_pytest_junit.is_file():
    exclude_patterns.append("local-pytest-evidence.rst")

# Required CI stays offline; live docs explicitly opt into external inventories.
intersphinx_mapping = {}
if os.getenv("SPHINX_ENABLE_INTERSPHINX") == "1":
    intersphinx_mapping = {
        "python": ("https://docs.python.org/3/", None),
    }

sphinx_gallery_conf = {
    "examples_dirs": "../examples/ternforge_docops",
    "gallery_dirs": "auto_examples",
    "filename_pattern": r".*\.py$",
    "backreferences_dir": "generated/backreferences",
    "doc_module": ("ternforge_docops",),
    "reference_url": {"ternforge_docops": None},
    "junit": "../test-results/sphinx-gallery/junit.xml",
    "remove_config_comments": True,
}

# sphinx-llm runs a dedicated markdown subprocess with this tag. Keep that
# derived build read-only: provider examples execute only in the primary docs build.
sphinx_tags = globals().get("tags")
if sphinx_tags is not None and sphinx_tags.has("sphinx_llm_markdown"):
    sphinx_gallery_conf["plot_gallery"] = False
