#!/usr/bin/env bash
set -euo pipefail
pass_count=0; warn_count=0; fail_count=0
pass() { printf '[PASS] %s\n' "$1"; pass_count=$((pass_count + 1)); }
warn() { printf '[WARN] %s\n' "$1"; warn_count=$((warn_count + 1)); }
fail() { printf '[FAIL] %s\n' "$1"; fail_count=$((fail_count + 1)); }
require_command() {
  if command -v "$1" >/dev/null 2>&1; then pass "Found $1"; else fail "Missing $1. $2"; fi
}
repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$repo_root"
# shellcheck disable=SC1091
source scripts/env/secrets.sh
printf '%s contributor doctor\n' "Ternforge DocOps"
printf 'Repo: %s\n\n' "$repo_root"
require_command git "Install Git."
require_command uv "Install uv."
require_command direnv "Install direnv and enable its shell or IDE integration."
if [ -x .venv/bin/python ]; then
  pass "Project virtualenv exists"
  if .venv/bin/python -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 13) else 1)'; then
    pass "Project Python is 3.13+"
  else
    fail "Project Python must be 3.13+."
  fi
else
  fail "Project virtualenv is missing. Run scripts/env/setup.sh."
fi
if uv lock --check >/dev/null 2>&1; then
  pass "uv.lock matches pyproject.toml"
else
  fail "uv.lock is stale or the installed uv does not match [tool.uv].required-version."
fi
config_files="$(py_lib_secret_env_files "$repo_root")" || config_files="__INVALID__"
if [ "$config_files" = "__INVALID__" ]; then
  fail "Could not read the project secret configuration."
elif [ -n "$config_files" ]; then
  require_command sops "This repository declares encrypted env files."
  if py_lib_load_secrets "$repo_root" >/dev/null; then
    pass "Declared secrets decrypt and load"
  else
    fail "Declared secrets could not be loaded."
  fi
else
  pass "Secret loader is an empty-configuration no-op"
fi
pre_commit_hook="$(git rev-parse --git-path hooks/pre-commit)"
pre_push_hook="$(git rev-parse --git-path hooks/pre-push)"
if [ -f "$pre_commit_hook" ] && [ -f "$pre_push_hook" ]; then pass "Git hooks are installed"; else warn "Git hooks are missing."; fi
if command -v gh >/dev/null 2>&1; then
  if gh auth status -h github.com >/dev/null 2>&1; then
    pass "GitHub CLI is authenticated"
  else
    warn "GitHub CLI is not authenticated."
  fi
else
  warn "GitHub CLI is optional and not installed."
fi
printf '\nSummary: %s passed, %s warnings, %s failed\n' "$pass_count" "$warn_count" "$fail_count"
[ "$fail_count" -eq 0 ]
