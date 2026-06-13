#!/usr/bin/env bash
# PostToolUse (Edit|Write|MultiEdit): auto-fix + format + type-check the edited
# Python file. Fast feedback so style/type drift never accumulates.
# Surfaces remaining problems to Claude via exit code 2 (stderr → model).
set -uo pipefail

root="${CLAUDE_PROJECT_DIR:-$PWD}"
# shellcheck source=/dev/null
source "$root/.claude/hooks/lib.sh"

payload="$(cat)"
file="$(edited_file_path "$payload")"
[ -n "$file" ] || exit 0
is_existing_py "$file" || exit 0

ruff="$(find_tool ruff)"
mypy="$(find_tool mypy)"
[ -n "$ruff$mypy" ] || exit 0   # toolchain not installed yet → no-op

problems=""

if [ -n "$ruff" ]; then
  "$ruff" check --fix --quiet "$file" >/dev/null 2>&1 || true
  "$ruff" format --quiet "$file" >/dev/null 2>&1 || true
  if ! out="$("$ruff" check --quiet "$file" 2>&1)"; then
    problems+="ruff:\n$out\n"
  fi
fi

if [ -n "$mypy" ]; then
  if ! out="$("$mypy" "$file" 2>&1)"; then
    problems+="mypy:\n$out\n"
  fi
fi

if [ -n "$problems" ]; then
  printf 'Lint/type issues remain in %s — fix them:\n%b' "$file" "$problems" >&2
  exit 2
fi
exit 0
