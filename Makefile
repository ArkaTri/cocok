# Cocok developer commands. Contract: docs/CHECKPOINTS.md §0.7.
# Every target runs through uv, so tool versions come from uv.lock.
SHELL := /bin/bash
.DEFAULT_GOAL := help
UV ?= uv
ZIZMOR_VERSION ?= 1.30.1
export ZIZMOR_VERSION

.PHONY: help setup lint fmt type test test-core test-int verify gate gates-upto

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

setup: ## Install all workspace packages + dev tools, install git hooks
	$(UV) sync --all-packages
	$(UV) run pre-commit install

lint: ## ruff (lint + format check) and import-linter layering contracts
	$(UV) run ruff check .
	$(UV) run ruff format --check .
	$(UV) run lint-imports

fmt: ## Auto-fix lint issues and format
	$(UV) run ruff check --fix .
	$(UV) run ruff format .

type: ## mypy --strict on core and adapters
	$(UV) run mypy

test: ## Fast tests (no integration, no slow)
	$(UV) run pytest -q -m "not integration and not slow"

test-core: ## Core tests + doctests with the 90% coverage gate
	$(UV) run pytest -q packages/core --doctest-modules --cov=cocok_core --cov-report=term-missing:skip-covered --cov-fail-under=90 -m "not slow"

test-int: ## Integration tests (testcontainers; needs Docker)
	$(UV) run pytest -q -m integration

verify: lint type test ## lint + type + fast tests

gate: ## Run one checkpoint gate: make gate CP=NN
	@test -n "$(CP)" || { echo "usage: make gate CP=NN"; exit 2; }
	@GATE_SINGLE=1 bash scripts/gates/cp$(CP).sh

gates-upto: ## Run every gate cp00..cpNN (fast steps; FULL=1 for slow ones)
	@test -n "$(CP)" || { echo "usage: make gates-upto CP=NN"; exit 2; }
	@for f in $$(ls scripts/gates/cp[0-9][0-9].sh | sort); do \
	  n=$$(basename $$f .sh); n=$${n#cp}; \
	  if [ "$$((10#$$n))" -le "$$((10#$(CP)))" ]; then echo "════ $$f"; bash $$f || exit 1; fi; \
	done
