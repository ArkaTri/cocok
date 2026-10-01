---
status: proposed
date: 2026-10-01
decision-makers: Arka
consulted: R2, R3, R5
blueprint-sections: "§5.1, §5.2 (B4), §15"
---

# ADR-0010: Production digital route starts with the PDF text layer; Docling must earn its RAM

## Context and Problem Statement

v2.0.0 sends digital PDFs through Docling (layout + tables) in production. Production is a 2 GB `t4g.small`
shared by Postgres, API, worker and Caddy. Docling's standard PDF pipeline loads PyTorch layout and
table-structure models; there is no published minimum RAM, and users report native memory growth on large
documents. Loading torch + Docling models in the worker could take most of the box.

Our digital documents are 1–3 page invoices/faktur with a clean text layer — the easiest case.

## Decision Drivers

* Fit the 2 GB host with headroom (target: total RSS < 1.6 GB at idle, < 1.9 GB peak).
* Keep Docling in the **benchmark** (it is a strong, recognizable baseline).
* Decide with numbers, not assumptions.

## Considered Options

1. Docling in production (v2.0.0).
2. **`pypdfium2` text + character boxes → LLM structuring (prod default). Docling = baseline B4 in eval.
   Adopt Docling in prod only if it wins on `automation_rate_at_1pct` for `invoice` **and** fits the memory budget.**
3. Larger instance (m7i-flex.large, 8 GB): ~5–6× the credit burn.

## Decision Outcome

Chosen option: **2**. The decision is re-evaluated at CP-13 with measured numbers:
`peak_rss_mb`, `p95_latency_s`, accuracy per route. Record the outcome in the EVAL_REPORT and, if Docling is
adopted, in a follow-up ADR.

### Consequences

* Good: worker image without torch (ONNX Runtime only) → smaller image, faster cold start, fits 2 GB.
* Good: text-layer char boxes give exact grounding for digital docs (ADR-0006).
* Bad: table-heavy invoices may lose structure. Mitigation: the LLM receives text with line order and
  x-coordinates (simple "layout text" rendering), which is usually enough for 1–3 page invoices.

### Confirmation

* CP-12 records `peak_rss_mb` for each B4 variant (`/usr/bin/time -v` or `psutil`).
* CP-30 gate: worker container memory limit `1g` in `compose.prod.yml`; smoke test processes 10 docs without OOM.

## More Information

* https://pypi.org/project/docling/ (2.131.0, 2026-09-29)
* https://github.com/docling-project/docling/issues/2877 (resource usage discussion)
