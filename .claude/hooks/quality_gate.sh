#!/usr/bin/env bash
# Stop: a turn must not end red. Runs the full gate (ruff + mypy + pytest) and
# blocks the stop (exit 2) with the failures if anything is broken.
# Loop-safe: if this stop is itself the result of a prior gate block, it allows
# the turn to end so the agent is never trapped.
set -uo pipefail

root="${CLAUDE_PROJECT_DIR:-$PWD}"
# shellcheck source=/dev/null
source "$root/.claude/hooks/lib.sh"

payload="$(cat)"
if [ "$(printf '%s' "$payload" | jq -r '.stop_hook_active // false' 2>/dev/null)" = "true" ]; then
  exit 0
fi

cd "$root" 2>/dev/null || exit 0

ruff="$(find_tool ruff)"
mypy="$(find_tool mypy)"
pytest="$(find_tool pytest)"

# Pre-scaffold: no toolchain and no source tree → nothing to gate.
[ -n "$ruff$mypy$pytest" ] || exit 0
[ -d src ] || [ -d tests ] || exit 0

failures=""

if [ -n "$ruff" ] && [ -d src ]; then
  out="$("$ruff" check . 2>&1)" || failures+="ruff:\n$out\n"
fi
if [ -n "$mypy" ] && [ -d src ]; then
  out="$("$mypy" src 2>&1)" || failures+="mypy:\n$out\n"
fi
if [ -n "$pytest" ] && [ -d tests ]; then
  out="$("$pytest" -q 2>&1)" || failures+="pytest (tail):\n$(printf '%s' "$out" | tail -25)\n"
fi

if [ -n "$failures" ]; then
  printf 'Quality gate is RED — resolve before ending the turn:\n%b' "$failures" >&2
  exit 2
fi
exit 0
