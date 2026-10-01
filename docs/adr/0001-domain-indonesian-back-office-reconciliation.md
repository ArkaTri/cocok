---
status: proposed  # DRAFT written by an AI agent (R8) — Arka edits, then sets status: accepted
date: 2026-10-01
decision-makers: Arka
consulted: R1
blueprint-sections: "§1"
---

# ADR-0001: Build an Indonesian back-office document reconciliation agent

## Context and Problem Statement

The portfolio project must prove end-to-end AI engineering (dataset creation, training from scratch and
fine-tuning, LLM/VLM integration, evaluation and calibration, production engineering, full stack) in a domain
where those skills are visibly needed by employers in Indonesia, Singapore and remote AI-engineering roles.

## Decision Drivers

* A real, unsolved pain: mixed digital and handwritten documents (faktur, nota, kwitansi, surat jalan) matched
  by hand against purchase orders; generic OCR silently outputs wrong values on handwriting.
* Data can be created legally (synthetic + composites from permissive datasets + own handwriting) — no scraping,
  no customer documents.
* The hard part is *knowing when not to trust the model* — a measurable, defensible metric (risk–coverage).
* Directly relevant to document-AI / AP-automation teams.

## Considered Options

1. Indonesian back-office document reconciliation (Cocok).
2. A generic RAG chatbot over documents.
3. A non-Indonesian receipts benchmark re-implementation (e.g., CORD-only).

## Decision Outcome

Chosen option: **1**, because it combines a local domain gap (no public Indonesian handwritten nota/kwitansi
dataset with field labels) with an evaluation-first story that generic RAG demos lack.

### Consequences

* Good: unique dataset and benchmark; deterministic Indonesian rules (terbilang, NPWP, PPN) show domain depth.
* Bad: handwriting variety in T3 is limited to one writer — disclosed in README and dataset card.

## More Information

<!-- Arka: add your own reasons here (why this domain matters to you, who you talked to, target companies). -->
