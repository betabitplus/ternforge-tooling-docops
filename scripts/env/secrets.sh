#!/usr/bin/env bash
# shellcheck shell=bash

py_lib_project_python() {
  local repo_root="${1:-$PWD}"
  if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
    printf '%s\n' "$VIRTUAL_ENV/bin/python"
  elif [ -x "$repo_root/.venv/bin/python" ]; then
    printf '%s\n' "$repo_root/.venv/bin/python"
  elif command -v uv >/dev/null 2>&1; then
    uv python find '>=3.13'
  else
    printf '%s\n' "Project Python 3.13+ is required. Run scripts/env/setup.sh." >&2
    return 1
  fi
}

py_lib_secret_env_files() {
  local repo_root="${1:-$PWD}"
  local python_bin
  python_bin="$(py_lib_project_python "$repo_root")" || return 1
  "$python_bin" - "$repo_root/pyproject.toml" <<'PY'
from __future__ import annotations
import sys
import tomllib
from pathlib import PurePosixPath

with open(sys.argv[1], "rb") as stream:
    pyproject = tomllib.load(stream)
files = pyproject.get("tool", {}).get("ternforge", {}).get("secrets", {}).get("env_files", [])
if not isinstance(files, list):
    raise SystemExit("[tool.ternforge.secrets].env_files must be a list.")
for value in files:
    if not isinstance(value, str) or not value.strip():
        raise SystemExit("Secret env file paths must be non-empty strings.")
    path = PurePosixPath(value.strip())
    if path.is_absolute() or ".." in path.parts:
        raise SystemExit("Secret env file paths must stay inside betabit-secrets.")
    print(path)
PY
}

py_lib_secrets_root() {
  printf '%s\n' "${XDG_DATA_HOME:-$HOME/.local/share}/betabit/secrets/betabit-secrets"
}

py_lib_ensure_secrets_repo() {
  local root branch
  root="$(py_lib_secrets_root)"
  if [ -d "$root/.git" ]; then
    git -C "$root" fetch --quiet --prune origin
    branch="$(git -C "$root" symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
    [ -z "$branch" ] || git -C "$root" merge --ff-only --quiet "origin/$branch"
  elif [ -e "$root" ]; then
    printf '%s\n' "Secret cache path is not a Git checkout: $root" >&2
    return 1
  else
    mkdir -p "$(dirname "$root")"
    git clone --quiet "${PY_LIB_SECRETS_GIT_URL:-https://github.com/betabitplus/betabit-secrets.git}" "$root"
  fi
  printf '%s\n' "$root"
}

py_lib_load_secrets() {
  local repo_root="${1:-$PWD}"
  local env_files config_root age_key_file env_file encrypted_env decrypted_env direnv_exports
  env_files="$(py_lib_secret_env_files "$repo_root")" || return 1
  [ -n "$env_files" ] || return 0
  command -v git >/dev/null 2>&1 || { printf '%s\n' "git is required." >&2; return 1; }
  command -v sops >/dev/null 2>&1 || { printf '%s\n' "sops is required for declared project secrets." >&2; return 1; }
  command -v direnv >/dev/null 2>&1 || { printf '%s\n' "direnv is required to export project secrets." >&2; return 1; }
  config_root="$(py_lib_ensure_secrets_repo)" || return 1
  age_key_file="$HOME/.config/sops/age/keys.txt"
  while IFS= read -r env_file; do
    [ -n "$env_file" ] || continue
    encrypted_env="$config_root/$env_file"
    [ -f "$encrypted_env" ] || { printf '%s\n' "Encrypted env file not found: $env_file" >&2; return 1; }
    if declare -F watch_file >/dev/null 2>&1; then watch_file "$encrypted_env"; fi
    if [ -z "${SOPS_AGE_KEY_FILE:-}" ] && [ -f "$age_key_file" ]; then
      decrypted_env="$(SOPS_AGE_KEY_FILE="$age_key_file" sops decrypt "$encrypted_env")" || return 1
    else
      decrypted_env="$(sops decrypt "$encrypted_env")" || return 1
    fi
    direnv_exports="$(printf '%s\n' "$decrypted_env" | direnv dotenv bash /dev/stdin)" || return 1
    eval "$direnv_exports" || return 1
  done <<EOF
$env_files
EOF
}
