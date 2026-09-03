"""Sphinx integration for retained Engineering Experiment reports."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from ternforge_docops._internal.experiments import discover_capsules

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.config import Config


def configure_experiment_mounts(app: Sphinx, config: Config) -> None:
    """Mount captured notebooks in place using sphinx-mounts."""
    root = Path(app.confdir).resolve().parent
    mounts: list[dict[str, object]] = []
    for capsule in discover_capsules(root):
        report = capsule / "report" / "report.ipynb"
        if not report.is_file():
            continue
        mounts.append(
            {
                "files": [str(report)],
                "mount_at": f"experiments/_generated/{capsule.name}",
                # MyST-NB materializes rich MIME outputs in the host build tree;
                # they are generated renderer resources, not source-path escapes.
                "path_check": "off",
            }
        )
    config.sources_from_toml = None
    config.mounts = mounts


def publish_experiment_inputs(app: Sphinx) -> None:
    """Publish raw-HTML media dependencies beside mounted report pages."""
    root = Path(app.confdir).resolve().parent
    output_root = Path(app.outdir) / "experiments" / "_generated"
    for capsule in discover_capsules(root):
        source = capsule / "inputs"
        if not source.is_dir():
            continue
        target = output_root / capsule.name / "inputs"
        shutil.rmtree(target, ignore_errors=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)
