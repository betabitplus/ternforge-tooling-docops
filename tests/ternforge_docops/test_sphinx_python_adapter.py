"""Hermetic acceptance tests for the Python Sphinx adapter."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from ternforge_docops._api import sphinx_python


def test_llm_markdown_child_does_not_adopt_parent_source_trace(tmp_path: Path) -> None:
    """A sphinx-llm child build must not delete its parent's transient source."""
    docs = tmp_path / "docs"
    docs.mkdir()
    target = docs / sphinx_python._SOURCE_TRACE_NAME
    target.write_text(sphinx_python._SOURCE_TRACE, encoding="utf-8")
    tags = SimpleNamespace(has=lambda name: name == "sphinx_llm_markdown")
    app = SimpleNamespace(confdir=str(docs), tags=tags)

    sphinx_python._materialize_source_trace(cast("Any", app), cast("Any", None))
    sphinx_python._cleanup_source_trace(cast("Any", app), None)

    assert target.read_text(encoding="utf-8") == sphinx_python._SOURCE_TRACE


def test_python_adapter_discovers_conventional_package(tmp_path: Path) -> None:
    """A conventional Python repo needs no project-specific gallery wiring."""
    docs = tmp_path / "docs"
    package = tmp_path / "src" / "demo_package"
    examples = tmp_path / "examples" / "demo_package"
    docs.mkdir()
    package.mkdir(parents=True)
    examples.mkdir(parents=True)

    (package / "__init__.py").write_text('"""Demo package."""\n', encoding="utf-8")
    (package / "implementation.py").write_text(
        "# @impl Demo implementation, IMPL_DEMO, [REQ_DEMO[revision==1]]\n",
        encoding="utf-8",
    )
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
        """[codelinks]
set_local_url = true
local_url_field = "source_url"

[codelinks.projects.python.source_discover]
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

   contract
   auto_examples/index
""",
        encoding="utf-8",
    )
    git = shutil.which("git")
    assert git is not None
    subprocess.run([git, "init", "--initial-branch=main", str(tmp_path)], check=True)
    subprocess.run(
        [git, "-C", str(tmp_path), "config", "user.name", "DocOps test"], check=True
    )
    subprocess.run(
        [git, "-C", str(tmp_path), "config", "user.email", "docops@example.invalid"],
        check=True,
    )
    subprocess.run(
        [
            git,
            "-C",
            str(tmp_path),
            "remote",
            "add",
            "origin",
            "https://github.com/example/demo.git",
        ],
        check=True,
    )

    (docs / "contract.rst").write_text(
        """Demo contract
=============

.. goal:: Demo goal
   :id: GOAL_DEMO

.. feature:: Demo feature
   :id: FEAT_DEMO
   :derives: GOAL_DEMO

.. req:: Demo requirement
   :id: REQ_DEMO
   :status: accepted
   :revision: 1
   :required_evidence: impl
   :derives: FEAT_DEMO
""",
        encoding="utf-8",
    )

    subprocess.run([git, "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        [git, "-C", str(tmp_path), "commit", "-m", "test fixture"], check=True
    )

    # Simulate a transient adapter page left by an abruptly interrupted build.
    (docs / "ternforge-python-source-trace.rst").write_text(
        sphinx_python._SOURCE_TRACE,
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
    assert "IMPL_DEMO" in (tmp_path / "html" / "needs.json").read_text(encoding="utf-8")
    assert not (docs / "ternforge-python-source-trace.rst").exists()
