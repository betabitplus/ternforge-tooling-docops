"""Python-project Sphinx adapter for Ternforge DocOps."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from sphinx_gallery.gen_gallery import DEFAULT_GALLERY_CONF

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.config import Config

_SOURCE_TRACE_NAME = "ternforge-python-source-trace.rst"
_SOURCE_TRACE = """:orphan:

Python implementation source ingestion
=======================================

.. src-trace::
   :project: python
"""
_OWNED_SOURCE_TRACE_APPS: set[int] = set()

_PYTHON_EXTENSIONS = (
    "sphinx_codelinks",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx_gallery.gen_gallery",
)


def _discover_package(repo_root: Path) -> str | None:
    """Return the single conventional Python package below ``src/``."""
    src = repo_root / "src"
    if not src.is_dir():
        return None
    packages = sorted(
        path.name
        for path in src.iterdir()
        if path.is_dir() and (path / "__init__.py").is_file()
    )
    return packages[0] if len(packages) == 1 else None


def _configure_source_links(config: Config) -> None:
    """Apply generic Python/Gherkin source links from consumer render context."""
    context = config.needs_render_context
    if (
        not isinstance(context, dict)
        or not {"source_base", "source_ref"} <= context.keys()
    ):
        return
    links = dict(config.needs_string_links)
    links.setdefault(
        "gherkin_feature_source",
        {
            "regex": r"(?P<path>features/.+\.feature)$",
            "link_url": "{{ source_base }}/{{ source_ref }}/{{ path }}",
            "link_name": "{{ path }}",
            "options": ["gherkin_feature"],
        },
    )
    links.setdefault(
        "pytest_module_source",
        {
            "regex": r"(?P<module>tests(?:\.[A-Za-z0-9_]+)+)$",
            "link_url": (
                "{{ source_base }}/{{ source_ref }}/{{ module | replace('.', '/') }}.py"
            ),
            "link_name": "{{ module | replace('.', '/') }}.py",
            "options": ["classname"],
        },
    )
    config.needs_string_links = links


def _materialize_source_trace(app: Sphinx, config: Config) -> None:
    """Create the Python adapter's transient source-trace ingestion page."""
    del config
    target = Path(app.confdir) / _SOURCE_TRACE_NAME
    if target.exists():
        if target.read_text(encoding="utf-8") != _SOURCE_TRACE:
            message = f"DocOps reserved source-trace path already exists: {target}"
            raise RuntimeError(message)
        return
    target.write_text(_SOURCE_TRACE, encoding="utf-8")
    _OWNED_SOURCE_TRACE_APPS.add(id(app))


def _cleanup_source_trace(app: Sphinx, exception: Exception | None) -> None:
    """Remove the adapter-owned transient source-trace page after the build."""
    del exception
    if id(app) not in _OWNED_SOURCE_TRACE_APPS:
        return
    (Path(app.confdir) / _SOURCE_TRACE_NAME).unlink(missing_ok=True)
    _OWNED_SOURCE_TRACE_APPS.discard(id(app))


def _configure_python(app: Sphinx, config: Config) -> None:
    """Apply conventional Python-project documentation defaults."""
    if config.src_trace_config_from_toml is None:
        config.src_trace_config_from_toml = "../ubproject.toml"
    _configure_source_links(config)

    package = _discover_package(Path(app.confdir).parent)
    if package is None or config.sphinx_gallery_conf != DEFAULT_GALLERY_CONF:
        return

    examples = Path(app.confdir).parent / "examples" / package
    examples_dirs = f"../examples/{package}" if examples.is_dir() else "../examples"
    config.sphinx_gallery_conf = {
        "examples_dirs": examples_dirs,
        "gallery_dirs": "auto_examples",
        "filename_pattern": r".*\.py$",
        "backreferences_dir": "generated/backreferences",
        "doc_module": (package,),
        "reference_url": {package: None},
        "copyfile_regex": r".*\.(?:png|pdf|mp4)$",
        "junit": "../test-results/sphinx-gallery/junit.xml",
        "remove_config_comments": True,
    }
    if app.tags.has("sphinx_llm_markdown"):
        config.sphinx_gallery_conf["plot_gallery"] = False


def setup(app: Sphinx) -> dict[str, Any]:
    """Register Python-specific documentation integrations."""
    app.setup_extension("ternforge_docops._api.sphinx")
    for extension in _PYTHON_EXTENSIONS:
        app.setup_extension(extension)
    app.connect("config-inited", _configure_python, priority=5)
    app.connect("config-inited", _materialize_source_trace, priority=10)
    app.connect("build-finished", _cleanup_source_trace)
    return {
        "version": "1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
