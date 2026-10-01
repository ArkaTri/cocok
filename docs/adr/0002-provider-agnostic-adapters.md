---
status: proposed  # DRAFT written by an AI agent (R8) — Arka edits, then sets status: accepted
date: 2026-10-01
decision-makers: Arka
consulted: R1, R3
blueprint-sections: "§6, §7.1, §15 (Portability)"
---

# ADR-0002: Keep every external provider behind a port (ports & adapters)

## Context and Problem Statement

Cocok uses several replaceable providers: LLM/VLM APIs (OpenAI, Gemini, Bedrock, Kaggle-hosted models), OCR
engines, object storage (S3 or local), a job queue, and a cloud host whose free plan ends around March 2027.
Model line-ups and prices change monthly. If provider SDKs leak into business logic, every change becomes a rewrite
and fair benchmarking between providers becomes impossible.

## Decision Drivers

* Swap providers by configuration, not code (portability, blueprint §15).
* Evaluate every route through the same harness and normalization (blueprint §11).
* Keep `core` pure and testable without network (blueprint §7.1).

## Considered Options

1. **Ports (`typing.Protocol` in `cocok_core.ports`) + adapters (`cocok_adapters`), wired only in composition
   roots (`deps.py`, `bootstrap.py`).**
2. Call provider SDKs directly from services/nodes.
3. A third-party LLM gateway library for everything.

## Decision Outcome

Chosen option: **1**. Ports expose domain types only; each port has one shared contract-test suite that every
adapter must pass; `import-linter` enforces that `core` imports no adapters, frameworks or I/O libraries.

### Consequences

* Good: providers are swappable per environment; tests run offline with fakes and recorded fixtures.
* Bad: a little more code (one adapter per provider). Accepted.

### Confirmation

`import-linter` contracts in `pyproject.toml` (CP-01) and contract tests per port (CP-22).
