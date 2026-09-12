"""Living Specifications report orchestration."""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404 - fixed git argv resolves the current source revision.
import tomllib
from collections.abc import Mapping
from pathlib import Path

from ternforge_docops._internal.allure.results import ExecutionKey
from ternforge_docops._internal.living_specs.evidence import load_examples
from ternforge_docops._internal.living_specs.models import (
    LivingAttachment,
    LivingExample,
    LivingSpecificationsReport,
)
from ternforge_docops._internal.living_specs.presentation import (
    render_pages,
    render_source,
)

_EMPTY_SOURCE = (
    "No BDD execution evidence was supplied to this build. "
    "Use the portal build with retained Allure results to render "
    "current executable behavior.\n"
)
_INLINE_MEDIA_TYPES = {"application/json", "text/plain"}


def _published_assets(
    examples: tuple[LivingExample, ...],
) -> tuple[LivingAttachment, ...]:
    """Collect unique non-inline attachments that must be copied into the portal."""
    attachments: list[LivingAttachment] = []
    for example in examples:
        attachments.extend(example.attachments)
        for step in example.steps:
            attachments.extend(step.attachments)
    return tuple(
        dict.fromkeys(
            attachment
            for attachment in attachments
            if attachment.source is not None
            and attachment.output_name is not None
            and attachment.media_type not in _INLINE_MEDIA_TYPES
        )
    )


def _repository_url(root: Path) -> str:
    """Return the consumer GitHub repository URL declared in project metadata."""
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return ""
    try:
        payload = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return ""
    project = payload.get("project")
    if not isinstance(project, dict):
        return ""
    urls = project.get("urls")
    if not isinstance(urls, dict):
        return ""
    value = str(urls.get("Repository") or "").strip().removesuffix(".git").rstrip("/")
    return value if value.startswith("https://github.com/") else ""


def _repository_revision(root: Path) -> str:
    """Resolve the revision rendered by this build without a Python Git API."""
    github_sha = os.environ.get("GITHUB_SHA", "").strip()
    if github_sha:
        return github_sha
    git = shutil.which("git")
    if git is None:
        return ""
    try:
        result = subprocess.run(  # nosec B603 - absolute git path and fixed argv.
            [git, "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip()


def _repository_source_base(root: Path) -> str:
    """Return a revision-pinned source base for generated implementation links."""
    repository = _repository_url(root)
    revision = _repository_revision(root)
    if not repository or not revision:
        return ""
    return f"{repository}/blob/{revision}"


def render_living_specifications(
    root: Path,
    raw_results: Path,
    *,
    result_links: Mapping[ExecutionKey, str] | None = None,
    coverage: Path | None = None,
) -> LivingSpecificationsReport:
    """Render current BDD evidence as narrative-first, theme-native RST."""
    examples = load_examples(
        root.resolve(),
        raw_results.resolve(),
        result_links=result_links,
        coverage=coverage,
    )
    if not examples:
        return LivingSpecificationsReport(source=_EMPTY_SOURCE, assets=())
    pages = render_pages(
        examples,
        repository_source_base=_repository_source_base(root),
    )
    return LivingSpecificationsReport(
        source=render_source(examples, pages),
        assets=_published_assets(examples),
        pages=pages,
    )


def publish_living_assets(
    report: LivingSpecificationsReport, output_root: Path
) -> None:
    """Publish only assets referenced by the generated Living Specifications report."""
    target = output_root / "_living-specs" / "assets"
    shutil.rmtree(output_root / "_living-specs", ignore_errors=True)
    if not report.assets:
        return
    target.mkdir(parents=True, exist_ok=True)
    for asset in report.assets:
        if asset.source is not None and asset.output_name is not None:
            shutil.copy2(asset.source, target / asset.output_name)
