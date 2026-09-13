"""Shared Sphinx extension for Ternforge engineering documentation."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING, Any

from sphinx_needs.api import add_field

from ternforge_docops._internal import (
    configure_experiment_mounts,
    configure_simplepdf_anchors,
    graph_config_path,
    publish_experiment_inputs,
    register_evidence_context,
    register_evidence_trust_view,
    register_review_views,
    register_specification_health_view,
    register_verification_assurance_view,
    register_verification_view,
    static_dir_path,
)

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.config import Config

_EXTENSIONS = (
    "myst_nb",
    "sphinx_mounts",
    "sphinx_design",
    "sphinx_needs",
    "sphinxcontrib.test_reports",
    "sphinx_llm.txt",
    "sphinx_simplepdf",
    "sphinx.ext.graphviz",
    "sphinxcontrib.mermaid",
)

_DEFAULT_NEED_ROLE_TITLE_LENGTH = 30
_SIMPLEPDF_MIME_PRIORITIES = [
    ("simplepdf", "text/html", 30),
    ("simplepdf", "image/svg+xml", 40),
    ("simplepdf", "image/png", 50),
    ("simplepdf", "image/gif", 60),
    ("simplepdf", "image/jpeg", 70),
    ("simplepdf", "text/markdown", 80),
    ("simplepdf", "text/latex", 90),
    ("simplepdf", "text/plain", 100),
]


def _configure_notebooks(config: Config) -> None:
    """Apply read-only notebook and MyST defaults used by retained evidence."""
    config.nb_execution_mode = "off"
    if config.nb_code_prompt_show == "Show code cell {type}":
        config.nb_code_prompt_show = "Show experiment code"
    if config.nb_code_prompt_hide == "Hide code cell {type}":
        config.nb_code_prompt_hide = "Hide experiment code"
    if not config.nb_mime_priority_overrides:
        config.nb_mime_priority_overrides = list(_SIMPLEPDF_MIME_PRIORITIES)
    if config.nb_render_markdown_format == "commonmark":
        config.nb_render_markdown_format = "myst"
    config.myst_enable_extensions = set(config.myst_enable_extensions) | {"colon_fence"}
    config.myst_fence_as_directive = set(config.myst_fence_as_directive) | {"mermaid"}
    if "auto_examples/*.ipynb" not in config.exclude_patterns:
        config.exclude_patterns.append("auto_examples/*.ipynb")


def _configure_presentation(config: Config) -> None:
    """Apply shared HTML, PDF, and Graphviz presentation defaults."""
    if config.html_theme == "alabaster":
        config.html_theme = "pydata_sphinx_theme"
    if config.html_theme == "pydata_sphinx_theme":
        html_context = dict(config.html_context)
        html_context.setdefault("default_mode", "auto")
        config.html_context = html_context
    package_static = str(static_dir_path())
    if package_static not in config.html_static_path:
        config.html_static_path.append(package_static)
    if "simplepdf_file_name" in config.values and config.simplepdf_file_name is None:
        config.simplepdf_file_name = "release-dossier.pdf"
    if config.graphviz_output_format == "png":
        config.graphviz_output_format = "svg"


def _configure_needs(config: Config) -> None:
    """Apply the canonical graph source and generic Needs presentation defaults."""
    if config.needs_from_toml is None:
        config.needs_from_toml = str(graph_config_path())
    if config.needs_flow_engine == "plantuml":
        config.needs_flow_engine = "graphviz"
    if config.needs_flow_direction == "down":
        config.needs_flow_direction = "left"
    if config.needs_role_need_max_title_length == _DEFAULT_NEED_ROLE_TITLE_LENGTH:
        config.needs_role_need_max_title_length = -1


def _configure_test_reports(config: Config) -> None:
    """Configure the common execution-evidence fields and conditional links."""
    config.tr_extra_options = [
        "verification_kind",
        "gherkin_feature",
        "gherkin_scenario",
        "nodeid",
        "scope_reach",
        "scope_basis",
        "external_reach",
    ]
    config.tr_property_link_types = {
        "verifies": "verifies",
        "produced_by": "produced_by",
    }
    config.tr_suite_id_length = 8
    config.tr_case_id_length = 8


def _configure_graph(app: Sphinx, config: Config) -> None:
    """Compose shared graph, notebook, presentation, and evidence defaults."""
    _configure_notebooks(config)
    _configure_presentation(config)
    _configure_needs(config)
    _configure_test_reports(config)
    if shutil.which("dot") is not None:
        app.tags.add("graphviz_available")


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
    app.add_css_file("ternforge-docops.css")
    register_specification_health_view(app)
    register_review_views(app)
    register_verification_view(app)
    register_evidence_context(app)
    register_evidence_trust_view(app)
    register_verification_assurance_view(app)
    app.connect("config-inited", configure_experiment_mounts, priority=5)
    app.connect("config-inited", _configure_graph, priority=6)
    app.connect("config-inited", _ensure_source_url_field, priority=12)
    app.connect("builder-inited", configure_simplepdf_anchors, priority=100)
    app.connect("builder-inited", publish_experiment_inputs, priority=600)
    return {
        "version": "1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
