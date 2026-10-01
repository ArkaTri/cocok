#!/usr/bin/env bash
# Shared helpers for checkpoint gate scripts — see docs/CHECKPOINTS.md §0.3.
#   step "<name>" <command...>   run a command, print ✔/✘ with duration, stop the gate on failure
#   slow_step "<name>" <cmd...>  like step, but skipped unless FULL=1 (or the gate is run alone)
#   pass cpNN                    print the final PASS line
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."

step() {
  local name="$1"; shift
  printf '▶ %s\n' "$name"
  local t0=$SECONDS
  if "$@"; then
    printf '  ✔ %s (%ss)\n' "$name" "$((SECONDS - t0))"
  else
    local rc=$?
    printf '  ✘ %s (exit %s) — re-run this command alone to debug (CHECKPOINTS §0.5)\n' "$name" "$rc"
    exit "$rc"
  fi
}

slow_step() {
  if [[ "${FULL:-0}" == "1" || "${GATE_SINGLE:-0}" == "1" ]]; then
    step "$@"
  else
    printf '▷ %s (SLOW — skipped; run with FULL=1)\n' "$1"
  fi
}

pass() { printf 'GATE %s: PASS\n' "$1"; }
