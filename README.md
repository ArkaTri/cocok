# Cocok

**An evaluation-first document reconciliation agent for Indonesian back-offices that knows when not to trust itself.**

Small businesses receive invoices, faktur, photographed *surat jalan* and handwritten *nota* / *kwitansi*. Cocok
extracts the fields, checks them with deterministic Indonesian rules (rupiah, *terbilang*, NPWP, PPN), scores a
**calibrated** confidence, and auto-processes a document **only when that is statistically safe** — everything
else goes to a human with the evidence highlighted on the image.

> Status: **under construction** — see [docs/PROGRESS.md](docs/PROGRESS.md). Numbers below will only appear once
> they exist in [docs/EVAL_REPORT.md](docs/EVAL_REPORT.md).

## Headline metric (fixed before building)

`automation_rate_at_1pct` — share of documents processed with no human while the field-level error rate among those
documents is ≤ 1 %, reported per test tier and document type, with confidence intervals and a *certified* operating
point (blueprint §2, ADR-0007).

## Persona

Back-office admin of a building-materials store (*toko bangunan*) that buys from many small suppliers.

## Repository map

| Path | What |
|---|---|
| `packages/core` | Pure domain logic (no I/O): models, validation, matching, confidence |
| `packages/adapters` | Implementations of core ports: DB, storage, LLM/VLM, OCR, queue |
| `packages/ml` | Data generation, training, evaluation (never imported at runtime) |
| `apps/api`, `apps/worker` | FastAPI service and the Procrastinate + LangGraph worker |
| `docs/` | Blueprint, checkpoints, function specs, ADRs, progress logs |

## Quickstart (development)

```bash
# Requires uv (https://docs.astral.sh/uv/) — it installs Python 3.13 for you.
make setup        # uv sync --all-packages + git hooks
make verify       # lint + types + fast tests
make gate CP=01   # run one checkpoint gate
```

## How this project is built

Read in this order: [docs/BLUEPRINT.md](docs/BLUEPRINT.md) → [docs/CHECKPOINTS.md](docs/CHECKPOINTS.md) →
[docs/FUNCTION_SPECS.md](docs/FUNCTION_SPECS.md). Workflow per checkpoint: brainstorm together → an AI agent
implements → Arka studies and tests it → sign-off ([ADR-0014](docs/adr/0014-workflow-ai-implements-arka-learns-and-verifies.md)).
The code is AI-written; the design decisions, verification and explanations are Arka's —
see [docs/HOW_I_USED_AI.md](docs/HOW_I_USED_AI.md).

## Limitations (known up front)

Indonesian-word handwriting variety in the real-handwriting tier comes from one writer's styles (blueprint §4.3).
