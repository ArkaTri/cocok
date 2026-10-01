---
status: proposed
date: 2026-10-01
decision-makers: Arka
consulted: R1, R3, R4, R5
blueprint-sections: "§6.4, §8, §9, §12, §16, §17"
---

# ADR-0012: Toolchain refresh (Oct 2026) — and what we deliberately did NOT change

## Context and Problem Statement

Arka asked to replace outdated tools with current industry choices. "Newest" is not the same as "best": a
tool should change only when (a) it is unmaintained/deprecated, (b) a successor removes real work or risk, or
(c) the old pin is incompatible with something we need. This ADR records both the changes and the refusals.

## Decision Outcome

### Changed

| Area | v2.0.0 | v2.1.0 | Reason |
|---|---|---|---|
| Postgres | 16 | **18** | Native `uuidv7()` (PK default without an extension); pgvector supports PG18 |
| Python runtime | 3.12 | **3.13 in containers/dev; `requires-python >=3.12`** | Longer support window; `ml` still installs on Kaggle's 3.12 runtime |
| DB driver | asyncpg | **psycopg 3** | One driver for SQLAlchemy, Procrastinate, LangGraph checkpointer (ADR-0004) |
| Queue | arq + Redis | **Procrastinate** | ADR-0004 |
| Auth libs | (unspecified) | **pwdlib[argon2]**; no JWT | ADR-0008 |
| Langfuse SDK | (unspecified) | **v4.x (OpenTelemetry-native, Mar 2026)** | v2-style `trace()/span()` APIs deprecated; v4 shares our OTel pipeline |
| MLflow | (unspecified) | **3.x** | Current major; `LoggedModel` + tracing |
| Next.js | (unspecified) | **16.x (16.3 current)** | Turbopack default, `proxy.ts` replaces `middleware.ts`, `next lint` removed → ESLint CLI flat config (or Biome) |
| transformers | (unspecified) | **v5** | Required by Qwen3.5 (ADR-0003) |
| Fine-tuning | LoRA/QLoRA | **Unsloth + TRL, 16-bit LoRA** | ADR-0003 |
| Augmentation | Albumentations | **torchvision v2 + own ops** | ADR-0009 |
| OCR in prod | — | **RapidOCR (ONNX)** | ADR-0006 grounding |
| Docs site | — | **Optional: Zensical** (+ built-in mkdocstrings replacement) | Material for MkDocs is in maintenance mode (EOL 2026-11-05); Zensical is the same team's successor. Plain Markdown in GitHub remains the source. |
| API fuzzing | — | **Schemathesis** (OpenAPI property-based tests) | Free contract hardening from the spec we already generate |
| Docstrings | "public functions have docstrings" | **Google style, `ruff` `D` rules + doctests in `core`** | Documentation that is tested (see FUNCTION_SPECS §0) |
| UUID in Python | — | **`uuid-utils`** (`uuid7()`) behind `IdGenerator` port | Python < 3.14 lacks `uuid.uuid7()`; IDs needed before insert for idempotency |

### Deliberately NOT changed (and why)

| Kept | Considered replacement | Why we kept it |
|---|---|---|
| **mypy --strict** | Astral **ty** | ty is still beta (0.0.81, 2026-09-15). Re-evaluate when 1.0 ships; ruff + uv already from Astral. |
| **pre-commit** | prek (Rust re-implementation) | pre-commit is the standard hooks spec; speed is irrelevant at our size. |
| **TrOCR-small** as the pretrained arm | PARSeq, small VLM | The experiment is "from scratch vs pretrained"; TrOCR is the canonical handwriting baseline and runs on CPU. |
| **CRNN + CTC** from scratch | — | Learning goal (§20). |
| **FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic** | Litestar, SQLModel | Industry default; no deficit. |
| **LangGraph** | Pydantic-AI graphs, plain Python | Kept (scoped by ADR-0005). |
| **Caddy, Docker Compose, single EC2** | k8s/ECS | Forbidden-by-cost list (§15) still correct. |
| **OpenTelemetry GenAI semconv** | — | Still *experimental* in 2026; use it, but pin the semconv version and do not build dashboards on unstable attribute names. |
| **Voyage-4 family** (if embeddings needed) | — | Current family (Jan 2026); still only "if needed". |

### Consequences

* Good: every change has a reason a reviewer can verify; refusals show judgment.
* Bad: transformers v5 + Qwen3.5 are new — expect upstream bugs. Mitigation: pin exact versions and HF revision
  hashes; Dependabot for ML deps is **monthly**, not weekly.

### Confirmation

* `docs/TECH_REFRESH_2026-10.md` lists each pin with the date verified.
* CP-01 gate checks `.python-version` = 3.13 and `requires-python = ">=3.12"`.

## More Information

* https://github.com/astral-sh/ty/releases · https://pypi.org/project/langfuse/ · https://pypi.org/project/mlflow/
* https://nextjs.org/blog/next-16-3 · https://makerkit.dev/blog/tutorials/nextjs-16
* https://squidfunk.github.io/mkdocs-material/blog/2025/11/05/zensical/
* https://www.postgresql.org/docs/current/release-18.html
