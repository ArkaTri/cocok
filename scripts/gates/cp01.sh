#!/usr/bin/env bash
# Gate CP-01 — monorepo skeleton + quality toolchain + CI (docs/CHECKPOINTS.md).
source "$(dirname "$0")/_lib.sh"
step "lockfile in sync"            uv sync --all-packages --frozen
step "lint (ruff + import-linter)" make --no-print-directory lint
step "types (mypy --strict)"       make --no-print-directory type
step "tests (cp01 smoke)"          uv run pytest -q -m cp01
step "pre-commit on all files"     uv run pre-commit run --all-files
step "actions pinned by full SHA"  bash scripts/gates/check_actions_pinned.sh
step "zizmor: no high findings"    bash -c 'find .github/workflows -name "*.yml" -size +0c -print0 | xargs -0 uvx "zizmor==${ZIZMOR_VERSION:-1.30.1}" --min-severity high'
step "python pins"                 bash -c 'test "$(cat .python-version)" = "3.13" && grep -q "requires-python = \">=3.12\"" pyproject.toml'
pass cp01
