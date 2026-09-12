"""Installed command facade for Ternforge DocOps."""

from __future__ import annotations

import argparse
from pathlib import Path

from ternforge_docops._internal import (
    VerificationEvidencePaths,
    build_dossier,
    build_html,
    build_portal,
    capture_experiment,
    discover_capsules,
    resolve_capsule,
    stale_resources,
    sync_resources,
    validate_experiments,
)


def _parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(prog="ternforge-docops")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root. Defaults to the current directory.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("sync", help="Materialize canonical DocOps resources.")
    commands.add_parser("check", help="Check canonical DocOps resources.")

    build = commands.add_parser(
        "build",
        help="Build documentation presentation from pre-existing evidence.",
    )
    build_commands = build.add_subparsers(dest="build_action", required=True)
    html = build_commands.add_parser("html", help="Build strict HTML documentation.")
    html.add_argument(
        "--junit", type=Path, help="Pre-generated JUnit evidence to import."
    )
    html.add_argument(
        "--coverage",
        type=Path,
        help="coverage.py JSON with per-test contexts from --show-contexts.",
    )
    html.add_argument("--output", type=Path, help="Output directory for rendered HTML.")
    html.add_argument(
        "--live-examples",
        action="store_true",
        help="Execute Sphinx-Gallery examples during trusted publication.",
    )
    dossier = build_commands.add_parser(
        "dossier",
        help="Build the release dossier with the upstream SimplePDF builder.",
    )
    dossier.add_argument(
        "--junit", type=Path, help="Pre-generated JUnit evidence to import."
    )
    dossier.add_argument(
        "--coverage",
        type=Path,
        help="coverage.py JSON with per-test contexts from --show-contexts.",
    )
    dossier.add_argument(
        "--output", type=Path, help="Output directory for dossier build files."
    )
    dossier.add_argument(
        "--allure-results",
        type=Path,
        help="Pre-generated Allure results used to materialize Living Specifications.",
    )
    portal = build_commands.add_parser(
        "portal",
        help="Build strict HTML with native Living Specs and forensic Allure results.",
    )
    portal.add_argument(
        "--junit", type=Path, help="Pre-generated JUnit evidence to import."
    )
    portal.add_argument(
        "--coverage",
        type=Path,
        help="coverage.py JSON with per-test contexts from --show-contexts.",
    )
    portal.add_argument("--output", type=Path, help="Output directory for the portal.")
    portal.add_argument(
        "--live-examples",
        action="store_true",
        help="Execute Sphinx-Gallery examples during trusted publication.",
    )
    portal.add_argument(
        "--allure-results",
        type=Path,
        required=True,
        help="Directory containing pre-generated Allure result files.",
    )

    experiments = commands.add_parser(
        "experiments",
        help="Validate or capture retained Engineering Experiments.",
    )
    experiment_commands = experiments.add_subparsers(dest="action", required=True)
    experiment_commands.add_parser("validate", help="Validate captured EXP reports.")
    capture = experiment_commands.add_parser(
        "capture",
        help="Capture one EXP report from an isolated capsule copy.",
    )
    capture.add_argument(
        "experiment",
        help="EXP number (for example 0001) or capsule directory name.",
    )
    return parser


def _check_resources(root: Path) -> int:
    """Report stale materialized DocOps resources for one repository."""
    stale = stale_resources(root)
    if not stale:
        print("DocOps resources are current.")
        return 0
    for path in stale:
        print(f"stale: {path.relative_to(root)}")
    return 1


def _validate_experiments(root: Path) -> int:
    """Validate every retained Engineering Experiment and print violations."""
    capsules = discover_capsules(root)
    if not capsules:
        print("No retained Engineering Experiment capsules found.")
        return 0
    failures = validate_experiments(root)
    for capsule, errors in failures.items():
        print(f"{capsule.relative_to(root)}:")
        for error in errors:
            print(f"  - {error}")
    if failures:
        return 1
    print(f"Validated {len(capsules)} Engineering Experiment capsule(s).")
    return 0


def _capture_experiment(root: Path, experiment: str) -> int:
    """Resolve and capture one retained Engineering Experiment capsule."""
    try:
        capsule = resolve_capsule(root, experiment)
        capture_experiment(capsule)
    except ValueError as exc:
        print(exc)
        return 1
    print(f"Captured {capsule.relative_to(root)} from an isolated temporary copy.")
    return 0


def _resolve_optional_path(path: Path | None) -> Path | None:
    """Resolve an optional CLI path without adding branching to command dispatch."""
    return None if path is None else path.resolve()


def main(argv: list[str] | None = None) -> int:
    """Run the DocOps command-line interface and return its exit status."""
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    if args.command == "sync":
        for path in sync_resources(root):
            print(path.relative_to(root))
        return 0
    if args.command == "check":
        return _check_resources(root)
    if args.command == "build":
        build_output = _resolve_optional_path(args.output)
        allure_results = _resolve_optional_path(getattr(args, "allure_results", None))
        evidence = VerificationEvidencePaths(
            junit=_resolve_optional_path(args.junit),
            allure_results=allure_results,
            coverage=_resolve_optional_path(args.coverage),
        )
        if args.build_action == "html":
            output = build_html(
                root,
                evidence=evidence,
                output=build_output,
                live_examples=args.live_examples,
            )
        elif args.build_action == "dossier":
            output = build_dossier(
                root,
                evidence=evidence,
                output=build_output,
            )
        else:
            output = build_portal(
                root,
                evidence=evidence,
                output=build_output,
                live_examples=args.live_examples,
            )
        print(output)
        return 0
    if args.action == "validate":
        return _validate_experiments(root)
    return _capture_experiment(root, str(args.experiment))
