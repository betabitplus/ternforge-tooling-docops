"""Python-project Sphinx adapter for Ternforge DocOps."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from sphinx_gallery.gen_gallery import DEFAULT_GALLERY_CONF

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.config import Config

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


def _configure_python(app: Sphinx, config: Config) -> None:
    """Apply conventional Python-project documentation defaults."""
    if config.src_trace_config_from_toml is None:
        config.src_trace_config_from_toml = "../ubproject.toml"

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
    return {
        "version": "1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
