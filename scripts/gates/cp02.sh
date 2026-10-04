#!/usr/bin/env bash
# Gate CP-02 — domain model, state machine, errors, ports (docs/CHECKPOINTS.md).
source "$(dirname "$0")/_lib.sh"
step "lockfile in sync"               uv sync --all-packages --frozen
step "lint (ruff + import-linter)"    make --no-print-directory lint
step "types (mypy --strict)"          make --no-print-directory type
step "fakes satisfy ports (mypy)"     uv run mypy packages/core/tests/test_ports.py
step "tests (cp02)"                   uv run pytest -q -m cp02
step "doctests (core models + errors)" uv run pytest -q --doctest-modules packages/core/src/cocok_core/models packages/core/src/cocok_core/errors.py
step "core coverage >= 90%"           uv run pytest -q packages/core --cov=cocok_core --cov-fail-under=90 -m "not slow"
step "schema snapshot unchanged"      uv run python -m cocok_core.schema_export --check schemas/extracted_document.schema.json
pass cp02
