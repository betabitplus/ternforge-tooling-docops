#!/usr/bin/env bash
set -euo pipefail
repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$repo_root"
printf '%s
' "Setting up development environment..."
if [ ! -f uv.lock ]; then
  printf '%s
' "Creating the initial uv.lock..."
  uv lock
fi
uv sync --locked --all-groups
uv run pre-commit install
printf '%s
' "Setup complete. Locked dependencies and configured hook stages are installed."
printf '%s\n' "Synchronizing Ternforge DocOps authoring resources..."
uv run ternforge-docops sync
