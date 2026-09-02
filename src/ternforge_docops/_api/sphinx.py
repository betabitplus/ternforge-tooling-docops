"""Shared Sphinx extension for Ternforge engineering documentation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sphinx_needs.api import add_field

from ternforge_docops._internal import graph_config_path, register_verification_view

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.config import Config

_EXTENSIONS = (
    "myst_nb",
    "sphinx_design",
    "sphinx_needs",
    "sphinxcontrib.test_reports",
    "sphinx_llm.txt",
    "sphinx_simplepdf",
    "sphinx.ext.graphviz",
    "sphinxcontrib.mermaid",
)


def _configure_graph(app: Sphinx, config: Config) -> None:
    """Apply shared graph, notebook, and execution-evidence defaults."""
    del app
    if config.needs_from_toml is None:
        config.needs_from_toml = str(graph_config_path())
    config.nb_execution_mode = "off"
    if config.html_theme == "alabaster":
        config.html_theme = "pydata_sphinx_theme"
    if "simplepdf_file_name" in config.values and config.simplepdf_file_name is None:
        config.simplepdf_file_name = "release-dossier.pdf"
    config.myst_fence_as_directive = set(config.myst_fence_as_directive) | {"mermaid"}
    if "auto_examples/*.ipynb" not in config.exclude_patterns:
        config.exclude_patterns.append("auto_examples/*.ipynb")
    config.tr_extra_options = [
        "verification_kind",
        "gherkin_feature",
        "gherkin_scenario",
    ]
    config.tr_property_link_types = {"verifies": "verifies"}
    config.tr_suite_id_length = 8
    config.tr_case_id_length = 8


def _ensure_source_url_field(app: Sphinx, config: Config) -> None:
    """Register the generic implementation source field when no adapter owns it."""
    del app
    if (
        getattr(config, "src_trace_set_local_url", False)
        and getattr(config, "src_trace_local_url_field", None) == "source_url"
    ):
        return
    add_field(
        "source_url",
        "Source URL for implementation evidence produced by a language adapter.",
        schema={"type": "string"},
    )


def setup(app: Sphinx) -> dict[str, Any]:
    """Register the shared Ternforge documentation stack."""
    for extension in _EXTENSIONS:
        app.setup_extension(extension)
    register_verification_view(app)
    app.connect("config-inited", _configure_graph, priority=5)
    app.connect("config-inited", _ensure_source_url_field, priority=12)
    return {
        "version": "1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
