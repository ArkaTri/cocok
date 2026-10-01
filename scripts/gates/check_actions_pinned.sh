#!/usr/bin/env bash
# ADR-0011: every third-party `uses:` must reference a 40-hex commit SHA (local ./ actions are exempt).
set -euo pipefail
cd "$(dirname "$0")/../.."
bad=$(grep -rnE '^\s*-?\s*uses:\s*' .github/workflows | grep -vE 'uses:\s*\./' | grep -vE '@[0-9a-f]{40}(\s|$)' || true)
if [[ -n "$bad" ]]; then
  echo "Unpinned actions (pin to a full commit SHA, add '# vX.Y.Z' comment):"
  echo "$bad"
  exit 1
fi
echo "all actions pinned"
