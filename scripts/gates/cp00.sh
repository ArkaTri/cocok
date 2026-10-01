#!/usr/bin/env bash
# Gate CP-00 — local toolchain present (accounts/budgets are checked by hand; see docs/progress/CP-00.md).
source "$(dirname "$0")/_lib.sh"
step "uv installed"            uv --version
step "git installed"           git --version
step "python >= 3.12 via uv"   uv run --no-sync python -c "import sys; assert sys.version_info >= (3, 12), sys.version"
for tool in docker pnpm gh; do
  if command -v "$tool" >/dev/null 2>&1; then
    printf '  ✔ %s present\n' "$tool"
  elif [[ "${STRICT_CP00:-0}" == "1" ]]; then
    printf '  ✘ %s missing (STRICT_CP00=1)\n' "$tool"; exit 1
  else
    printf '  ⚠ %s missing — needed from CP-21 (docker), CP-26 (pnpm); gh optional\n' "$tool"
  fi
done
pass cp00
