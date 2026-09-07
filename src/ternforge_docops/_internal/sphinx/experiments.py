"""Sphinx integration for retained Engineering Experiment reports."""

from __future__ import annotations

import html
import re
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sphinx_needs.api import get_needs_view

from ternforge_docops._internal.experiments import discover_capsules

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.config import Config


_EXP_PAGE_PATTERN = re.compile(
    r"^experiments/_generated/exp_(?P<number>[0-9]{4})_[^/]+/report$"
)


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


def inject_experiment_page_metadata(
    app: Sphinx,
    pagename: str,
    templatename: str,
    context: dict[str, Any],
    doctree: object,
) -> None:
    """Expose graph-owned EXP provenance to HTML without authoring it twice."""
    del templatename, doctree
    match = _EXP_PAGE_PATTERN.fullmatch(pagename)
    if match is None:
        return

    need_id = f"EXP_{match.group('number')}"
    needs = get_needs_view(app)
    need = needs.get(need_id)
    if need is None:
        return

    experiment_date = html.escape(str(need.get("experiment_date", "")), quote=True)
    tags = [
        (
            '<meta name="ternforge-exp-id" '
            f'content="{html.escape(need_id, quote=True)}">'
        ),
        (f'<meta name="ternforge-exp-date" content="{experiment_date}">'),
    ]
    for target_id in need.get("informs", []):
        target = needs.get(str(target_id))
        if target is None:
            continue
        tags.append(
            '<meta name="ternforge-exp-inform" '
            f'content="{html.escape(str(target_id), quote=True)}" '
            f'data-docname="{html.escape(str(target.get("docname", "")), quote=True)}">'
        )
    context["metatags"] = f"{context.get('metatags', '')}{''.join(tags)}"
