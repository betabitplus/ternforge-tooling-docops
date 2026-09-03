"""Hermetic acceptance tests for the Python Sphinx adapter."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_python_adapter_discovers_conventional_package(tmp_path: Path) -> None:
    """A conventional Python repo needs no project-specific gallery wiring."""
    docs = tmp_path / "docs"
    package = tmp_path / "src" / "demo_package"
    examples = tmp_path / "examples" / "demo_package"
    docs.mkdir()
    package.mkdir(parents=True)
    examples.mkdir(parents=True)

    (package / "__init__.py").write_text('"""Demo package."""\n', encoding="utf-8")
    (examples / "GALLERY_HEADER.rst").write_text(
        "Demo examples\n=============\n",
        encoding="utf-8",
    )
    (examples / "example.py").write_text(
        '"""Example\n=======\n"""\n\nvalue = 1\n',
        encoding="utf-8",
    )
    (examples / "fixture.png").write_bytes(b"retained media")
    (tmp_path / "ubproject.toml").write_text(
        """[codelinks.projects.python.source_discover]
src_dir = "src"
include = ["**/*.py"]
comment_type = "python"

[codelinks.projects.python.analyse.oneline_comment_style]
start_sequence = "@impl"
end_sequence = "\\n"
field_split_char = ","

[[codelinks.projects.python.analyse.oneline_comment_style.needs_fields]]
name = "title"

[[codelinks.projects.python.analyse.oneline_comment_style.needs_fields]]
name = "id"

[[codelinks.projects.python.analyse.oneline_comment_style.needs_fields]]
name = "implements"
type = "list[str]"

[[codelinks.projects.python.analyse.oneline_comment_style.needs_fields]]
name = "type"
default = "impl"
""",
        encoding="utf-8",
    )
    (docs / "conf.py").write_text(
        'project = "demo-project"\n'
        'extensions = ["ternforge_docops._api.sphinx_python"]\n'
        'root_doc = "index"\n',
        encoding="utf-8",
    )
    (docs / "index.rst").write_text(
        """Demo docs
=========

.. toctree::
   :maxdepth: 1

   auto_examples/index
""",
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            "-m",
            "sphinx",
            "-W",
            "--keep-going",
            "-D",
            "plot_gallery=0",
            "-b",
            "html",
            str(docs),
            str(tmp_path / "html"),
        ],
        check=True,
    )

    assert (tmp_path / "html" / "auto_examples" / "index.html").is_file()
    assert (docs / "auto_examples" / "fixture.png").read_bytes() == b"retained media"
