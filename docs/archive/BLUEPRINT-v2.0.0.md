# COCOK — Project Blueprint (v2)

```yaml
doc_id: cocok-blueprint
version: 2.0.0            # semver; bump on every accepted change to this file
status: approved-for-build
owner: Arka               # human; final decision maker on every open question
created: 2026-10-01
language_policy: "Code, docs, commits in English. Domain terms stay Indonesian (see §23 Glossary). UI copy in Indonesian."
repo_location_of_this_file: docs/BLUEPRINT.md
```

---

## 0. Rules for AI agents reading this file

- This file is the **single source of truth (SSOT)**. Precedence when instructions conflict:
  1. Explicit instruction from Arka in the current session
  2. This blueprint
  3. Accepted ADRs in `docs/adr/`
  4. Agent judgment
- Keywords **MUST / MUST NOT / SHOULD / MAY** follow RFC 2119.
- Read order: §1–§3 (what and why) → §19 (your role brief) → §20 (ownership policy) → sections your role references.
- **Do not invent requirements.** If something is ambiguous or missing: propose 2–3 options with trade-offs, ask Arka, then record the decision as an ADR.
- Any change to architecture, data contracts, metrics, or this file → one PR that updates this file **and** adds an ADR, and bumps `version`.
- One concern per PR. Small PRs. No drive-by refactors in bug-fix PRs.
- Recommended repo setup: keep this file at `docs/BLUEPRINT.md`; add a short `AGENTS.md` (and/or `CLAUDE.md`) at repo root that says: "Read docs/BLUEPRINT.md first. Follow §20 ownership policy."

---

## 1. Project identity

| Item | Value |
|---|---|
| Name | **Cocok** (Indonesian: "match") |
| One-liner | An evaluation-first document reconciliation agent for Indonesian back-offices that **knows when not to trust itself**. |
| Problem | Small businesses receive mixed documents: digital invoices and tax invoices (faktur), photographed delivery notes (surat jalan), handwritten notes and receipts (nota, kwitansi). Manual data entry and matching against purchase orders is slow and error-prone. Common OCR tools degrade on low-quality or handwritten documents and silently output wrong values. |
| Core idea | Extract → validate deterministically → score calibrated confidence → **automate only when safe**, route everything else to a human with grounded evidence (field ↔ location on the image). |
| Default persona | Back-office admin of a building-materials store (toko bangunan) or small distributor that receives goods from many small suppliers. *(Open decision D1.)* |
| Portfolio purpose | Prove, end-to-end: dataset creation, model training (from scratch + fine-tuning), LLM/VLM integration, evaluation and calibration, production engineering, full-stack delivery. |
| Target employers | Document-AI / AP-automation teams (e.g., Indonesian spend-management and OCR companies), AI-engineering roles requiring RAG/agents/eval/production (Indonesia, Singapore, remote). |

### 1.1 Goals
- **G1** Publish a dataset that does not exist publicly: Indonesian nota/kwitansi-style documents with field-level labels, including real human handwriting tiers.
- **G2** Benchmark extraction strategies (OCR pipeline, zero-shot API VLM, zero-shot small VLM, fine-tuned small VLM) on cost, latency, and accuracy.
- **G3** Train two models: an amount reader (from-scratch CRNN vs fine-tuned TrOCR experiment) and a LoRA-fine-tuned small VLM.
- **G4** Calibrated confidence with abstention; report a risk–coverage curve and an ablation study.
- **G5** A deployed, secure, observable, documented web application with human-in-the-loop review.
- **G6** Everything reproducible and portable across clouds.

### 1.2 Non-goals (MUST NOT build)
- Not an accounting system, not tax filing, no Coretax/e-Faktur integration.
- No real customer documents in the public repo or published datasets.
- No training of large models from scratch.
- No multi-tenant SaaS billing, no payments.
- No scraping of web images (Google Images, Pinterest, etc.).

---

## 2. Success metrics (fixed before building; MUST NOT be changed after seeing results without an ADR)

```yaml
headline_metric:
  id: automation_rate_at_1pct
  definition: "Share of documents auto-processed (no human) while the field-level error rate among auto-processed documents is <= 1%."
  report_per: [test_tier, doc_type]
  visualization: risk_coverage_curve
metrics:
  - id: field_accuracy
    definition: "Exact match after normalization, per field, per doc_type, per test_tier."
  - id: amount_exact_match
    definition: "Exact match of total_amount (critical field), per test_tier."
  - id: calibration_ece
    definition: "Expected Calibration Error of per-field confidence (15 bins), plus reliability diagram."
  - id: aurc
    definition: "Area under the risk-coverage curve (lower is better)."
  - id: ablation_delta
    definition: "Change in automation_rate_at_1pct when one confidence signal is removed (esp. the second amount reader)."
  - id: cost_per_doc_usd
    report: [p50, p95, per_route]
  - id: latency_s
    report: [p50, p95, per_route]
  - id: discrepancy_detection
    definition: "Precision/recall of planted discrepancies (total mismatch, terbilang mismatch, qty vs PO, duplicate doc number)."
targets: "No vanity targets. Report honestly. CI gates are non-regression gates only (see §11)."
```

---

## 3. Scope

### 3.1 Document types

| doc_type | Typical form | Role in system | Data source |
|---|---|---|---|
| `purchase_order` | Structured record | Source of truth from the buyer's system | Synthetic (generated) |
| `invoice` | Digital PDF (has text layer), incl. faktur-style | Vendor claim | Synthetic + Arka's own documents (redacted) |
| `nota` / `kwitansi` | Photo of handwritten receipt | Vendor claim (small suppliers) | Synthetic, composites, Arka's handwriting |
| `surat_jalan` | Photo of printed/handwritten delivery note | Proof of delivery | Synthetic + Arka's handwriting |

### 3.2 Canonical extraction schema (all doc types share it; optional fields may be null)

```yaml
ExtractedDocument:
  doc_type: enum[purchase_order, invoice, nota, kwitansi, surat_jalan]
  vendor_name: str
  vendor_npwp: str|null        # normalized to 16 digits (see §5.5)
  vendor_nitku: str|null       # 22 digits
  doc_number: str|null
  doc_date: date|null
  po_reference: str|null
  payer_name: str|null         # kwitansi "Sudah terima dari"
  line_items:
    - description: str
      qty: decimal
      unit: str|null
      unit_price: Money|null
      line_total: Money|null
  subtotal: Money|null
  tax_amount: Money|null
  total_amount: Money          # critical field
  amount_in_words: str|null    # terbilang, raw text as written
  received_by: str|null
FieldMeta (per field):
  value_raw: str
  value_normalized: any
  confidence: float            # calibrated P(correct)
  bbox: [page, x0, y0, x1, y1] | null
  signals: dict                # per-signal values used by the calibrator
Money: { amount_idr: int }     # integer rupiah, never float
```

### 3.3 MVP vs later
- **MVP (Milestones A–C):** all four doc types, extraction, validators, confidence + abstention, PO matching, review UI, auth, deploy, observability, backups.
- **Later (backlog, only after C is done):** vendor memory (if not finished in C), n8n email intake, MCP server exposing read-only tools, read-only text-to-SQL analytics, RAG over contract clauses.

---

## 4. Data plan

### 4.1 Sources and licenses (verify each license file at download time; record in `data/LICENSES.md`)

| source_id | Source | Content | License | Allowed use in Cocok |
|---|---|---|---|---|
| `synth` | Own scenario generator (§4.2) | PO, invoice, nota, kwitansi, surat jalan rendered from scenarios | Own; publish as CC BY 4.0 | Train, validation, calibration, test tier T0; publish |
| `names` | Kaggle `landlord/handwriting-recognition` (~400k handwritten names, real writers) | Handwritten name crops | CC0 | Pretraining (official train split only); composites T2 (official test split only); publish |
| `cvl_hds` | CVL Handwritten Digit Strings (~300 writers) | Real handwritten digit strings | CC BY-NC 3.0 | Amount-reader fine-tuning (train split); evaluation (test split); composites T2 may be published under NC with attribution; **non-commercial only** |
| `orand_car` | ORAND-CAR-2014 (real bank-check amounts) | Courtesy-amount images | CC BY-NC-ND 4.0 | **Evaluation as-is only.** MUST NOT modify, composite, or redistribute |
| `cord` | CORD v2 (Indonesian printed receipts) | Receipt images + labels | CC BY 4.0 | Optional baseline comparability only |
| `own_hand` | Arka's own handwriting (2–3 deliberate styles) | Full Indonesian nota/kwitansi/surat jalan | Own | Test tier T3; publish |

**Prohibited data:** web-scraped images; real third-party documents in any public artifact; AI-generated handwriting in **any test tier**.

### 4.2 Scenario generator (ground truth is created first, documents are rendered from it)
- Generates fictional transactions: vendor, items, quantities, prices, totals, terbilang, dates, NPWP (15-digit legacy and 16-digit formats), NITKU, PO references.
- Planted perturbations with labels: total ≠ sum of lines, terbilang ≠ total, qty mismatch vs PO, price mismatch vs PO, duplicate doc number, legacy NPWP format, missing required field.
- Renderers:
  - `digital`: HTML template → PDF (text layer present).
  - `handwriting_like`: handwriting fonts + stroke-width/jitter augmentation (training only).
  - `composite`: paste real handwritten crops (`names`, `cvl_hds`) into kwitansi/nota templates; record bbox per field.
  - `photo_sim`: perspective, blur, shadow, low light, JPEG compression, paper texture, crumple (Albumentations).
- Every rendered item ships with JSON ground truth + per-field bbox from the renderer.
- Deterministic: seeded RNG; generator config versioned (`datagen/config/*.yaml`); generator version recorded in manifests.
- All generated identifiers (NPWP, NIK, NITKU, phone numbers) MUST be random and fictional; dataset card states this explicitly.

### 4.3 Test tiers

| Tier | Content | Writers | Measures |
|---|---|---|---|
| T0 | Held-out synthetic (all doc types) | n/a | Sanity, regression |
| T1 | `cvl_hds` test split + `orand_car` test split, as-is | Hundreds of real writers | Amount reader |
| T2 | Composite kwitansi/nota: templates + `names` test crops + `cvl_hds` test digit strings | Hundreds of real writers | Document-level extraction on real strokes |
| T3 | Arka's handwriting: 30–50 Indonesian documents, 2–3 styles, varied photo conditions | 1 person, multiple styles | Indonesian-specific end-to-end (terbilang, item names, formats) |

Known limitation (MUST appear in README and dataset card): Indonesian-word handwriting variety is limited to one person's styles in T3.

### 4.4 Splits and leakage rules (MUST)
- Training uses only: `synth` train split, `names` train split, `cvl_hds` train split.
- Calibration fitting uses a dedicated **calib** split (synthetic val + a fixed subset of T2 marked `calib`). Calib items MUST NOT appear in reported test results.
- No test-tier item (by sha256 and by source id) may appear in any training or calibration set. A CI job (`data-leakage-check`) MUST fail on overlap.
- Source crops (e.g., a `cvl_hds` digit string) used inside T2-calib composites MUST be excluded from T1 and T2-test reporting.
- Report metrics on T0, T1, T2-test, T3 separately. Never pool tiers in the headline without also showing per-tier numbers.

### 4.5 Storage and versioning
- Raw data is **not** stored in git. Use object storage or a Hugging Face dataset repo (private until license review passes).
- `data/manifests/*.parquet` in git: `item_id, sha256, source_id, license, split, tier, doc_type, generator_version, created_at`.
- Dataset releases are tagged (`cocok-docs-v0.1`, …) with a dataset card (`docs/DATASET_CARD.md`).
- A publish script MUST refuse to upload items whose license is `CC-BY-NC-ND` or whose source is not publishable.

### 4.6 Privacy and ethics
- Own documents (e.g., personal receipts) are redacted before storage; never published unredacted.
- Any helper writer (optional) signs a short written consent for publication of their handwriting.
- Synthetic content is fictional; no real persons or businesses are implied.

---

## 5. Model plan

### 5.1 Routing (per document)
1. Detect input kind: PDF with text layer → `digital` route; image or scanned PDF → `visual` route.
2. `digital`: Docling parse (layout + tables) → LLM structuring into `ExtractedDocument`.
3. `visual`: primary VLM extraction (fine-tuned small VLM **only if** it wins the benchmark; otherwise best API VLM).
4. **Always** run the amount reader on the `total_amount` crop (bbox from primary extractor) as an independent second read.
5. Deterministic validators and the confidence model run on every route.

### 5.2 Baselines (Milestone A)
- **B1** OCR pipeline: PaddleOCR-VL or GLM-OCR → text LLM structuring.
- **B2** Zero-shot API VLMs. Preferred free source: Kaggle Community Benchmarks model access (daily credit allowance) **if image input is supported** (verify); otherwise OpenAI (remaining credits), Bedrock (AWS credits), or Gemini free tier (**synthetic data only**).
- **B3** Zero-shot small open VLM (Qwen3-VL-2B-Instruct class).
- **B4** Docling for digital PDFs.
- All baselines run through the same eval harness and the same normalization code.

### 5.3 Fine-tuned VLM (Milestone B)
- Base: `Qwen/Qwen3-VL-2B-Instruct` (or same-class successor). Record exact HF revision hash.
- Method: LoRA / QLoRA; vision tower frozen in v1; output = JSON matching §3.2 schema.
- Training data: `synth` train split (+ composites built from train splits only).
- Compute: Kaggle T4 (≈30 GPU-h/week quota) → fallback Modal free monthly credits → RunPod only if >16 GB VRAM is required (hard cap: $10 total).
- Deliverables: adapter on HF Hub, `docs/MODEL_CARD.md` section, MLflow run, Kaggle training notebook.
- Adoption rule: use as primary `visual` extractor only if it beats the best zero-shot route on `automation_rate_at_1pct`, or matches it at materially lower cost/latency. Otherwise document "fine-tuning not worth it for this task" with evidence — this is a valid outcome.

### 5.4 Amount reader experiment (Milestone B)
- **Option A — from scratch:** CRNN + CTC in PyTorch. Pretrain on `names` train split; fine-tune on synthetic Rupiah amount crops + `cvl_hds` train split. Charset: digits, `.`, `,`, `-`, `R`, `p`, space.
- **Option B — pretrained:** `microsoft/trocr-small-handwritten` fine-tuned on the same data.
- Select the winner by exact match on T1; report both, including training cost and inference latency on CPU.
- The selected model runs on CPU in production (must fit the small server).

### 5.5 Deterministic components (no ML; HUMAN-OWNED, see §20)
- `terbilang`: Indonesian number words ↔ integer (handles "se-", "belas", "puluh", "ratus", "ribu", "juta", "miliar", "rupiah", common misspellings).
- `money`: parse/format `Rp 1.250.000,-`, `1.250.000`, `Rp1250000`, etc. → integer rupiah.
- `dates`: Indonesian month names and numeric formats → ISO date.
- `npwp`: normalize and validate. 16-digit NPWP; legacy 15-digit corporate NPWP → prefix `0`; personal NPWP equals NIK (16 digits); NITKU = 22 digits. Formatting characters stripped.
- `arithmetic`: line_total = qty × unit_price; subtotal = Σ line_total; total = subtotal + tax (tolerance from rules).
- `tax`: rates and bases loaded from `rules/tax.yaml` with effective dates. **MUST NOT hardcode VAT rates** (Indonesian VAT rules changed recently; verify current regulation when writing the rule file).

### 5.6 Confidence and abstention (HUMAN-OWNED, see §20)
- Per-field signals: primary model score (token log-prob if available, else self-consistency over N=2–3 samples on hard cases), agreement between primary and amount reader, terbilang ↔ amount agreement, validator pass/fail, cross-field arithmetic consistency, vendor-memory agreement (when available).
- Calibrator: logistic regression or isotonic regression fit on the **calib** split → calibrated P(correct) per field.
- Policy: a document is auto-approved only if every required field ≥ threshold τ. τ is chosen on the calib split to keep field error ≤ 1% among auto-approved docs. τ is stored in `rules/confidence.yaml` with a version.
- Reports: risk–coverage curve, reliability diagram, ECE, and ablation (remove each signal; especially the amount reader).

### 5.7 Vendor memory (Milestone C, SHOULD)
- Human corrections are stored and keyed by normalized vendor NPWP, then vendor name.
- Retrieval: exact key lookup first; fuzzy name match (trigram) second; embeddings only if both fail and evidence shows benefit. Do not use vectors where a key lookup works.
- Uses: few-shot examples for the API route; automatic regression test cases.
- Measure before/after on a repeat-vendor subset.

### 5.8 Experiment tracking
- MLflow (local/sqlite backend; artifacts to object storage). Every run logs: git SHA, data manifest version, config, metrics, model artifacts.
- Notebooks are for exploration only. Training/eval code lives in `packages/ml`; Kaggle notebooks install the package at a pinned commit and call its CLI.

---

## 6. System architecture

```
[Next.js web (Vercel)] --HTTPS--> [Caddy] --> [FastAPI api] --enqueue--> [Redis] --> [Worker: LangGraph pipeline]
                                                  |                                        |
                                    [PostgreSQL 16 + pgvector] <---------------------------+
                                    [Object storage: S3 or local]                          |
                                                                                           +--> Model adapters: API VLM | local VLM | OCR | amount reader
                                                                                           +--> Langfuse (LLM traces), OpenTelemetry, structured logs
```

### 6.1 Pipeline (LangGraph, Postgres checkpointer)
`ingest → detect_input_kind → classify_doc_type → route → extract → read_amount → validate → score_confidence → match_against_po → decide → persist → emit_events`
- `decide` → `AUTO_APPROVED` or `NEEDS_REVIEW` (LangGraph interrupt; resumes on human action).
- Every node: typed input/output (Pydantic), idempotent, timeout, retries with exponential backoff + jitter on retryable errors only.
- Pipeline version string recorded on every run.

### 6.2 Document status state machine (enforced in `core`; invalid transitions raise a domain error)
```
UPLOADED → QUEUED → PROCESSING → EXTRACTED → {AUTO_APPROVED | NEEDS_REVIEW}
NEEDS_REVIEW → {APPROVED | REJECTED}
AUTO_APPROVED | APPROVED → POSTED
PROCESSING → FAILED (retry_count, reason) → QUEUED (manual or auto retry, max 3)
```

### 6.3 API (REST, `/api/v1`, OpenAPI is the contract)
- `POST /documents` (multipart; `Idempotency-Key` header) → `202 {document_id, job_id}`
- `GET /documents/{id}` · `GET /documents/{id}/extraction` · `GET /documents/{id}/file` (short-TTL presigned URL)
- `PATCH /documents/{id}/fields/{field}` (correction, with reason)
- `POST /documents/{id}/approve` · `POST /documents/{id}/reject`
- `GET /review-queue?sort=confidence&page=…`
- `GET|POST /purchase-orders` · `GET /documents/{id}/match`
- `GET /metrics/summary` (admin)
- `GET /healthz` (liveness) · `GET /readyz` (DB, Redis, storage)
- Errors: RFC 9457 `application/problem+json`. Pagination: cursor-based.

### 6.4 Data model (Postgres; UUIDv7 primary keys; `timestamptz` UTC)
- `users`, `roles`, `user_roles`
- `vendors` (normalized_npwp unique nullable, name, aliases)
- `purchase_orders`, `po_lines`
- `documents` (sha256 unique, doc_type, status, storage_key, uploaded_by, pipeline_version)
- `extraction_runs` (document_id, route, model_id, model_revision, adapter_version, prompt_id, prompt_version, rules_version, code_sha, latency_ms, cost_usd, raw_output jsonb)
- `extracted_fields` (run_id, field, value_raw, value_normalized jsonb, confidence, bbox, signals jsonb)
- `corrections` (field_id, old_value, new_value, user_id, reason)
- `match_results` (document_id, po_id, status, discrepancies jsonb)
- `audit_log` (append-only: actor, action, entity, before, after, at)
- Every prediction is traceable to (code SHA, model + revision, adapter, prompt version, rules version, pipeline version).

---

## 7. Repository structure (monorepo)

```
cocok/
├── AGENTS.md                      # 10 lines: read docs/BLUEPRINT.md first; follow §20
├── README.md
├── pyproject.toml                 # uv workspace root
├── apps/
│   ├── api/src/cocok_api/
│   │   ├── main.py                # app factory only
│   │   ├── deps.py                # composition root: wires ports → adapters
│   │   ├── routers/               # HTTP only: parse, authz, call service, map errors
│   │   ├── services/              # use-cases orchestrating core + ports
│   │   ├── schemas/               # request/response DTOs
│   │   ├── auth/                  # password hashing, tokens, RBAC guards
│   │   └── middleware/            # request id, logging, security headers, rate limit
│   ├── worker/src/cocok_worker/
│   │   ├── bootstrap.py           # composition root for worker
│   │   ├── graph.py               # LangGraph wiring only
│   │   ├── nodes/                 # one file per pipeline node
│   │   └── tasks.py               # queue entrypoints
│   └── web/                       # Next.js (TypeScript), pnpm
├── packages/
│   ├── core/src/cocok_core/       # DOMAIN: pure Python. No I/O. No framework imports.
│   │   ├── models/                # entities, value objects (Money, Npwp, DocumentStatus)
│   │   ├── validation/            # npwp, money, terbilang, dates, arithmetic   [HUMAN-OWNED]
│   │   ├── matching/              # po_matching, tolerances                       [HUMAN-OWNED]
│   │   ├── confidence/            # signals, calibrator, policy                   [HUMAN-OWNED]
│   │   ├── ports/                 # Protocols: Extractor, AmountReader, Storage, Repository, LLMClient, Clock
│   │   └── errors.py
│   ├── adapters/src/cocok_adapters/
│   │   ├── db/                    # SQLAlchemy models + repositories
│   │   ├── storage/               # s3.py, local.py (same contract tests)
│   │   ├── llm/                   # bedrock.py, openai.py, gemini.py, kaggle_proxy.py
│   │   ├── vlm/                   # local_qwen.py
│   │   ├── ocr/                   # docling.py, paddle.py
│   │   └── amount_reader/         # crnn.py or trocr.py (ONNX/CPU inference)
│   └── ml/src/cocok_ml/           # training + eval; NEVER imported by api/worker at runtime
│       ├── datagen/               # scenario generator, renderers, augmentations
│       ├── train/crnn/            # model + training loop                         [HUMAN-OWNED]
│       ├── train/trocr/  train/vlm_lora/
│       ├── eval/                  # metrics, risk-coverage, reports              [metrics HUMAN-OWNED]
│       └── calibrate/
├── prompts/                       # *.md with front matter: id, version, model_family
├── rules/                         # tax.yaml, tolerances.yaml, confidence.yaml (versioned, effective dates)
├── data/manifests/                # parquet manifests; no raw data
├── evals/                         # eval configs + baseline.json for CI gate
├── migrations/                    # Alembic
├── infra/
│   ├── docker/                    # Dockerfiles (multi-stage, non-root)
│   ├── compose/                   # compose.dev.yml, compose.prod.yml
│   ├── caddy/Caddyfile
│   └── scripts/                   # deploy.sh, rollback.sh, backup.sh, restore.sh
├── docs/                          # see §17
└── .github/workflows/             # ci-python.yml, ci-web.yml, eval-gate.yml, data-checks.yml, security.yml, deploy.yml
```

### 7.1 Layering rules (MUST; enforced by `import-linter` in CI)
- `core` imports nothing from `adapters`, `api`, `worker`, `ml`. No network, disk, DB, or clock access in `core` (time comes through the `Clock` port).
- `api` and `worker` depend on `core` ports; concrete adapters are injected only in `deps.py` / `bootstrap.py`.
- `ml` may import `core` (to reuse validators and terbilang); `api`/`worker` MUST NOT import `ml`.
- Soft limits (ruff-enforced where possible): file ≤ 300 lines, function ≤ 50 lines, cyclomatic complexity ≤ 10. Exceptions require a one-line justification comment.

---

## 8. Tech stack (pin all versions in lockfiles; upgrade via Dependabot PRs)

```yaml
python: "3.12"
python_tooling: [uv (workspaces), ruff, mypy (strict for core + adapters), import-linter, pytest, pytest-asyncio, hypothesis, testcontainers, coverage, pre-commit]
backend: [fastapi, pydantic v2, pydantic-settings, sqlalchemy 2 (async), alembic, asyncpg, redis, arq, langgraph (+postgres checkpointer), httpx, tenacity, structlog, opentelemetry, langfuse]
ml: [torch, transformers, peft, accelerate, bitsandbytes (GPU only), datasets, albumentations, scikit-learn, mlflow, docling, paddleocr (eval only), onnxruntime (CPU inference)]
web: [next.js (app router), typescript strict, tailwind, shadcn/ui, tanstack query, openapi-typescript + openapi-fetch, zod, react-pdf/pdf.js, vitest, playwright, eslint, prettier, pnpm]
infra: [docker (multi-arch arm64+amd64), docker compose, caddy, aws ec2 graviton (t4g), ecr, ssm parameter store, s3, vercel, github actions (OIDC to AWS)]
security_tooling: [gitleaks, pip-audit, pnpm audit, trivy, dependabot]
observability: [langfuse cloud hobby, opentelemetry, sentry (free tier, optional)]
embeddings_if_needed: [voyage-4 family (free token allowance) or local open-source model]
```

---

## 9. Engineering standards (MUST)

- **Typing:** all public functions typed; `mypy --strict` on `core` and `adapters`.
- **Errors:** typed domain errors in `core/errors.py`; no bare `except`; API maps errors to problem+json; never return stack traces to clients.
- **Logging:** structlog JSON to stdout; every line carries `request_id` / `job_id` / `document_id`; a redaction processor removes secrets and personal data.
- **Config:** pydantic-settings, 12-factor; `.env.example` documents every variable; app fails fast at startup on invalid config.
- **API contract:** OpenAPI generated from FastAPI; TypeScript client generated in CI; breaking changes require `/api/v2`.
- **DB migrations:** Alembic only; every migration has a working downgrade; CI runs upgrade → downgrade → upgrade on an empty DB; breaking schema changes use expand → migrate → contract across separate releases.
- **Jobs:** idempotent (key = document sha256 + pipeline version); retries only on retryable errors; failures land in `FAILED` with a reason.
- **External calls:** explicit timeouts on every call; per-route fallback; cost recorded per call.
- **Prompts:** files in `prompts/` with `id` and `version`; version logged on every LLM call; any prompt change triggers the eval gate.
- **Business rules:** data in `rules/*.yaml`, schema-validated at startup; never hardcoded.
- **Money:** integer rupiah only; never floats.
- **Git:** trunk-based, short-lived branches, PR required for `main`, conventional commits, squash merge, semver tags, `CHANGELOG.md` (Keep a Changelog).
- **Code review checklist (every PR):** tests added/updated · layering respected · no secrets · migrations reversible · docs/ADR updated if behavior or architecture changed · `ai-assisted` label if applicable.

---

## 10. Testing strategy and bug-fix protocol

- **Unit (core):** fast, no I/O; coverage gate ≥ 90% lines on `core`.
- **Property-based (Hypothesis):** terbilang round-trip (int → words → int); money parse ↔ format round-trip; NPWP normalization idempotent; arithmetic invariants.
- **Contract tests:** one shared suite per port, run against every adapter (e.g., `Storage` against s3 and local; `LLMClient` against recorded fixtures).
- **Integration:** adapters with testcontainers (Postgres, Redis); LLM adapters use recorded responses (no live calls in CI except the eval gate).
- **Golden tests:** fixed documents with expected deterministic outputs (validators, matching) to catch regressions.
- **E2E:** API flow test; Playwright critical path upload → review → correct → approve.
- **Overall coverage gate:** ≥ 75%.
- **Bug-fix protocol (MUST):** reproduce → write a failing test → minimal fix → full suite green → `docs/FAILURE_LOG.md` entry if user-visible or model-related (date, symptom, root cause, fix, test added) → no unrelated changes in the same PR.
- **Flaky tests are bugs:** quarantine with a label and open an issue the same day.

---

## 11. Evaluation harness and CI eval gate

- CLI: `cocok-eval run --route <route_id> --tiers T0,T1,T2,T3 --out evals/results/<run_id>/`
- Outputs: `metrics.json`, `report.md`, plots (risk–coverage, reliability diagram, per-field accuracy), per-item predictions for error analysis.
- Same normalization code (`core.validation`) for every route, so comparisons are fair.
- **Eval gate** runs on PRs touching `prompts/`, `rules/`, `adapters/llm|vlm|ocr|amount_reader`, `core/confidence`, `core/validation`:
  - Fixed subset: ≤ 30 documents across tiers; cost cap per run (default $0.50; configurable).
  - Compare with `evals/baseline.json`. Fail if `automation_rate_at_1pct` drops > 2 points, or any critical field accuracy drops > 3 points (thresholds in `evals/gate.yaml`).
  - Updating the baseline requires an explicit PR with justification.
- Full evaluation: manual or scheduled; results summarized in `docs/EVAL_REPORT.md` with dataset version, model revisions, prompt versions, code SHA.

---

## 12. Observability

- **Traces:** OpenTelemetry spans for API requests and every pipeline node; LLM/VLM calls traced in Langfuse with prompt id/version, model, tokens, cost, latency, route.
- **Logs:** structlog JSON → stdout; Docker log rotation enabled.
- **Errors:** Sentry for api, worker, web (free tier; optional but recommended).
- **Product metrics** (computed from DB, shown on `/dashboard`): documents processed, auto-approve rate, abstain rate, correction rate per field, cost per doc, p95 latency per route, queue depth, failure rate.
- **Health:** `/healthz`, `/readyz`; worker heartbeat key in Redis.
- **Alerts (minimal, free):** scheduled GitHub Action uptime check; failure rate above threshold; daily LLM spend above cap; AWS Budget alarms.

---

## 13. Security (baseline: OWASP ASVS Level 1 + OWASP Top 10 for LLM Applications)

**Authentication and authorization**
- Passwords hashed with argon2id; short-lived access token + rotating refresh token in httpOnly, Secure, SameSite cookies; CSRF protection for cookie-authenticated mutations.
- RBAC roles: `viewer`, `staff`, `manager`, `admin`. Approving documents requires `manager`. Role changes are audited.
- Public demo uses seeded sandbox accounts; one user's uploads are never visible to another; demo data auto-purged after N days (configurable).

**File and input handling**
- Allowlist by magic bytes: PDF, JPEG, PNG, WEBP. Limits: file size (default 10 MB), pages (default 10), pixels (decompression-bomb guard).
- Images re-encoded on ingest; PDF JavaScript never executed; original filenames never used as paths (storage key = UUID).
- Files stored private; served only via short-TTL presigned URLs after an authorization check.

**LLM-specific**
- Document content is untrusted data. The system never follows instructions found inside documents.
- All model outputs are validated against Pydantic schemas; invalid output → retry once → `NEEDS_REVIEW`.
- No tool execution derived from document text. Future text-to-SQL MUST run under a read-only DB role with `statement_timeout` and a table allowlist.

**Platform**
- Secrets: SSM Parameter Store in prod; `.env` locally (gitignored); gitleaks in pre-commit and CI.
- GitHub → AWS via OIDC; least-privilege IAM roles; no long-lived access keys.
- Containers: multi-stage builds, minimal base images, non-root user, read-only root filesystem where possible; Trivy scan in CI fails on fixable HIGH/CRITICAL.
- Dependencies: Dependabot, pip-audit, pnpm audit in CI.
- Network: HTTPS only (Caddy automatic TLS); security headers (HSTS, CSP, X-Content-Type-Options, Referrer-Policy, frame-ancestors); CORS allowlist; rate limits on auth and upload endpoints; DB and Redis never exposed publicly; server access via SSM Session Manager instead of open SSH.
- Database: application role with least privilege; separate migration role.
- `audit_log` is append-only (no UPDATE/DELETE grants for the app role).
- `SECURITY.md` describes how to report vulnerabilities.
- Threat model (STRIDE-lite) reviewed at the end of each milestone.

---

## 14. Data management, backup and recovery

- **PostgreSQL:** nightly `pg_dump -Fc` → encrypted (age) → S3 bucket with versioning and lifecycle (7 daily, 4 weekly, 3 monthly). Weekly encrypted copy to a second location outside the primary cloud.
- **Object storage:** bucket versioning on; lifecycle rules purge demo uploads after the retention period.
- **Pre-deploy backup:** `deploy.sh` takes a backup before running migrations.
- **Targets:** RPO ≤ 24 h, RTO ≤ 2 h.
- **Restore drill (MUST):** monthly scripted restore into a scratch database + smoke test; result logged in `docs/RUNBOOK.md`. A backup that has never been restored does not count as a backup.

---

## 15. Deployment, environments and portability

**Environments:** `local` (docker compose) · `prod` (single EC2 t4g + docker compose + Caddy) · web on Vercel with preview deployments per PR.

**CI/CD (GitHub Actions)**
- On PR: lint, typecheck, import-linter, unit + integration tests, migration up/down test, data-leakage check, security scans, Docker build, web tests, eval gate (when triggered).
- On merge to `main`: build multi-arch images tagged with git SHA → push to ECR → deploy via SSM Run Command: backup → pull → migrate → start → readiness check → **automatic rollback** to the previous SHA if readiness fails.
- `infra/scripts/rollback.sh <sha>`; keep the last 5 images.

**Portability (MUST)**
- The core system runs with only Docker + PostgreSQL + Redis + local or any S3-compatible storage.
- Every cloud service sits behind a port (Storage, LLMClient); provider choice by environment variables.
- Documented migration targets: Oracle Cloud Always Free (Arm; currently 2 OCPU / 12 GB) or split hosting (Vercel + managed Postgres free tier + container host). Multi-arch images make the move a config change, not a rebuild.

**Cost guardrails**
- AWS account is on the Free Plan (created ~2026-09-07; plan ends ~early March 2027). Decision D3 due by February 2027: upgrade to Paid (credits remain usable until their expiry) or migrate.
- Complete the five AWS credit activities (Budget, EC2, RDS, Lambda, Bedrock) early; delete test resources afterwards.
- App-level caps: per-document cost cap, daily LLM spend cap, kill switch `PAID_MODELS_ENABLED=false`.
- MUST NOT provision: NAT Gateway, ALB, EKS, always-on GPU instances, SageMaker endpoints.
- The fine-tuned 2B VLM is **not** served on the CPU server. Production uses API VLM + CPU amount reader; the fine-tuned model is published on Hugging Face with its benchmark results.

---

## 16. Frontend (`apps/web`)

**Pages**
- `/login`
- `/upload` — drag-and-drop, multiple files, per-file progress and status
- `/queue` — `NEEDS_REVIEW` list; filter by doc type/vendor; sort by lowest confidence
- `/documents/[id]` — image/PDF viewer (left) with bbox overlays; fields (right) with confidence badges and evidence (which signals disagreed); inline correction with reason; approve/reject; keyboard shortcuts
- `/purchase-orders` — list, detail, match status and discrepancies
- `/dashboard` — automation rate, abstain rate, cost per doc, latency, correction hotspots by field/vendor
- `/about` — method, limitations, links to eval report, dataset, models

**Standards**
- TypeScript strict; API access only via the generated client; Zod for form validation.
- Every view has loading, empty, and error states.
- Accessibility: labels, focus order, keyboard use, sufficient contrast.
- No secrets in client code; auth via httpOnly cookies.
- Playwright e2e for the critical path.
- UI copy in Indonesian (persona); code and docs in English.

---

## 17. Documentation set ("documented" means all of these exist and are current)

| File | Content |
|---|---|
| `README.md` | First screen in plain language: what, why, headline metric + risk–coverage chart, 90-second demo video, live link, architecture image, quickstart, limitations |
| `docs/ARCHITECTURE.md` | C4 context + container diagrams, pipeline, state machine, data model |
| `docs/adr/NNNN-title.md` | MADR template: context, options, decision, consequences |
| `docs/RUNBOOK.md` | Deploy, rollback, backup, restore (+ drill log), rotate secrets, incident checklist |
| `docs/EVAL_REPORT.md` | Latest full evaluation with versions |
| `docs/DATASET_CARD.md` | Sources, licenses, tiers, splits, limitations, fictional-data statement |
| `docs/MODEL_CARD.md` | Per model: base, data, training cost, metrics, limitations, intended use |
| `docs/SECURITY.md` | Reporting process, threat model summary |
| `docs/FAILURE_LOG.md` | Date, symptom, root cause, fix, test added |
| `docs/HOW_I_USED_AI.md` | What AI generated, what Arka wrote or changed, which modules are human-owned |
| `CONTRIBUTING.md`, `CHANGELOG.md` | Workflow, commit conventions, release notes |

Code comments explain *why*, not *what*. Public functions have docstrings.

---

## 18. Milestones (pause-safe: each one ends with a publishable artifact)

```yaml
milestones:
  - id: M0
    name: Foundation
    weeks: [1]
    deliverables:
      - Repo with monorepo skeleton, pre-commit, CI (lint, typecheck, tests, import-linter, gitleaks)
      - docs/BLUEPRINT.md (this file), AGENTS.md, README (problem + persona + metrics), ADR-0001 domain choice, ADR-0002 provider-agnostic adapters
      - Pydantic schemas (§3.2), data/LICENSES.md, downloaded sources with manifests
      - Scenario generator v0 + digital renderer
      - First 15–20 handwritten documents by Arka (T3 seed)
      - AWS Budget configured
    done_when:
      - CI green on main; schemas have unit tests; manifests pass leakage check
  - id: A
    name: Data + baselines
    weeks: [1, 2, 3]
    deliverables:
      - Dataset v0.1 with tiers T0–T3 and calib split
      - Eval harness v1 (§11) with risk–coverage and reliability plots
      - Baselines B1–B4 evaluated; docs/EVAL_REPORT.md v0.1
      - Dataset card; publishable parts on Hugging Face
      - Optional: Kaggle Community Benchmark (if image input supported)
      - LinkedIn post 1 (benchmark findings)
    done_when:
      - Every baseline has per-tier metrics, cost and latency; report reproducible from one command
  - id: B
    name: Models + calibration
    weeks: [4, 5, 6]
    deliverables:
      - Amount reader experiment (CRNN from scratch vs TrOCR fine-tune) with report
      - VLM LoRA fine-tune with adoption decision (§5.3)
      - Calibrator + abstention policy + ablation study
      - MLflow runs; model cards; adapters/models on Hugging Face
      - EVAL_REPORT v0.2
    done_when:
      - Risk–coverage curve and ablation reproducible; adoption decisions recorded as ADRs
  - id: C
    name: Product
    weeks: [7, 8, 9, 10]
    deliverables:
      - API, worker pipeline, validators, PO matching, state machine
      - Review UI with grounding, auth/RBAC, dashboard
      - Observability (§12), security baseline (§13), backups + first restore drill (§14)
      - Deploy with automatic rollback (§15)
      - Vendor memory (SHOULD; else backlog)
      - README final, 90-second video, LinkedIn post 2
    done_when:
      - Live demo; Playwright critical path green; restore drill logged; security checklist §13 complete
backlog_after_C: [n8n email intake, MCP server (read-only tools), read-only text-to-SQL analytics, RAG over contract clauses]
```

Rule: if the bootcamp final project interrupts, stop at the end of the current milestone, not in the middle. Work items are broken into issues of ≤ 1 day, each with acceptance criteria.

---

## 19. Role briefs for AI agents

Each agent reads §0–§3, its own brief, §20, and the sections listed under "references".

### R1 — Architect / Tech Lead
- **Mission:** keep the system coherent with this blueprint.
- **Owns:** this file, ADRs, issue breakdown per milestone, PR review for layering and standards.
- **Must:** break milestones into ≤ 1-day issues with acceptance criteria; reject PRs that violate §7.1 or §9; keep the open-decisions list (§22) current.
- **Must not:** change metrics or scope without Arka's approval and an ADR.
- **References:** §6, §7, §9, §18, §21, §22.

### R2 — Data & ML Engineer
- **Mission:** data generation, training, and experiment tracking.
- **Owns:** `packages/ml/datagen`, `train/trocr`, `train/vlm_lora`, `calibrate/` plumbing, manifests, Kaggle notebooks, MLflow, model cards, dataset card.
- **Must:** respect licenses (§4.1) and leakage rules (§4.4); make every run reproducible (§5.8); report negative results.
- **Must not:** write the implementation of human-owned modules (§20); use AI-generated handwriting in any test tier.
- **References:** §4, §5, §11.

### R3 — Backend Engineer
- **Mission:** API, worker, adapters, database.
- **Owns:** `apps/api`, `apps/worker`, `packages/adapters`, `migrations/`, `core/models` and `core/ports`.
- **Must:** follow §6 contracts and §9 standards; idempotent jobs; reversible migrations; contract tests per adapter.
- **Must not:** implement human-owned modules; import `ml` at runtime; put I/O into `core`.
- **References:** §3.2, §6, §7, §9, §10, §13.

### R4 — Frontend Engineer
- **Mission:** the review experience.
- **Owns:** `apps/web`.
- **Must:** use the generated API client; implement §16 pages and states; Playwright critical path.
- **Must not:** call model providers from the browser; store tokens in localStorage.
- **References:** §6.3, §16, §13.

### R5 — DevOps / SRE
- **Mission:** reliable, cheap, portable operations.
- **Owns:** `infra/`, CI/CD workflows, OIDC/IAM, SSM, backups and restore scripts, monitoring and alerts, cost guardrails.
- **Must:** automatic rollback; pre-deploy backup; monthly restore drill; multi-arch images; Budget alarms.
- **Must not:** provision anything listed as forbidden in §15.
- **References:** §12, §13, §14, §15.

### R6 — QA / Evaluation
- **Mission:** catch regressions before users and recruiters do.
- **Owns:** test plans, property tests, golden tests, eval gate wiring, flaky-test triage.
- **Must:** write the failing test first for every reported bug (§10); keep `evals/baseline.json` honest.
- **References:** §2, §10, §11.

### R7 — Security Reviewer
- **Mission:** keep the baseline in §13 true.
- **Owns:** threat model per milestone, review of auth/upload/LLM-input code, triage of scanner findings.
- **References:** §13, §14.

### R8 — Documentation
- **Mission:** make the project understandable in 10 seconds (recruiter) and 10 minutes (engineer).
- **Owns:** §17 document set, CHANGELOG, diagrams; drafts `HOW_I_USED_AI.md` from PR labels for Arka to edit.
- **Must not:** claim results that are not in `EVAL_REPORT.md`.
- **References:** §1, §2, §17.

---

## 20. Ownership and AI-assist policy (MUST)

**Why:** Arka must be able to explain, debug, and rebuild the core logic from scratch in interviews. The project fails its purpose if the core is written by agents.

**HUMAN-OWNED modules (Arka writes the implementation):**
- `packages/core/validation/*` (npwp, money, terbilang, dates, arithmetic)
- `packages/core/matching/*`
- `packages/core/confidence/*` (signals, calibrator, policy)
- `packages/ml/eval/` metric functions (accuracy, ECE, risk–coverage, AURC)
- `packages/ml/train/crnn/` (model definition + training loop)

**For human-owned modules, agents MAY:** write specs and interfaces, write test cases (including property-based tests), explain concepts, review Arka's code, point out bugs, give hints or pseudocode.

**For human-owned modules, agents MUST NOT:** write or paste a complete implementation. If asked, give hints and remind Arka of this policy. Arka may override for a specific module only by recording it in an ADR.

**Everything else:** agents may implement; Arka reviews every PR and must be able to explain it. PRs with substantial AI-generated code carry the `ai-assisted` label and are summarized in `docs/HOW_I_USED_AI.md`.

---

## 21. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Indonesian-word handwriting variety limited to Arka's styles | High | Medium | Disclose; multi-writer tiers T1/T2 cover critical fields; optional helper writers |
| Fine-tuned VLM does not beat zero-shot | Medium | Low | Valid finding; keep API route; document in ADR |
| Kaggle Benchmarks lacks image input or needed models | Medium | Low | Fall back to remaining OpenAI credits, Bedrock (AWS credits), Gemini free tier (synthetic only) |
| Scope creep | High | High | Milestone gates; backlog list; R1 enforces |
| License violation (ORAND ND, CVL NC) | Medium | High | License field in manifests; publish script blocks non-publishable sources |
| Data leakage between splits | Medium | High | sha256 + source-id overlap check in CI |
| AWS Free Plan ends (~Mar 2027) | Certain | Medium | Portability (§15); decision D3 by Feb 2027 |
| LLM cost overrun | Low | Medium | Per-doc and daily caps; kill switch; Budget alarms |
| Bootcamp final project interrupts | Medium | Medium | Pause-safe milestones |
| Prompt injection via document text | Medium | Medium | §13 LLM rules; schema validation; no tools from document content |

---

## 22. Open decisions (owner: Arka)

| ID | Decision | Default until decided |
|---|---|---|
| D1 | Exact persona | Building-materials store receiving goods from small suppliers |
| D2 | UI language | Indonesian UI, English docs |
| D3 | AWS after Free Plan: upgrade to Paid vs migrate | Decide by Feb 2027; migrate if no card risk is acceptable |
| D4 | Publish benchmark on Kaggle Community Benchmarks | Yes, if image input and terms allow |
| D5 | License for published dataset | CC BY 4.0 for own/synthetic parts; CC BY-NC for parts derived from CVL; ORAND never published |

---

## 23. Glossary (Indonesian domain terms)

| Term | Meaning |
|---|---|
| nota | Handwritten or printed sales note from a small shop |
| kwitansi | Payment receipt; typically has "Sudah terima dari" (received from), amount in digits, and amount in words |
| surat jalan | Delivery note accompanying goods |
| faktur (pajak) | (Tax) invoice |
| PO | Purchase order |
| terbilang | Amount written in words, e.g., "satu juta seratus ribu rupiah" |
| NPWP | Taxpayer ID; 16 digits (legacy corporate 15-digit IDs are prefixed with 0; personal NPWP equals NIK) |
| NIK | National ID number (16 digits) |
| NITKU | Business-activity-place ID (22 digits) |
| PPN | Value-added tax (VAT) |
| DPP | Tax base |
| Coretax | Indonesian tax administration system |
| UMKM | Micro, small and medium enterprises |
| Rp format | `Rp 1.250.000,-` → dot = thousands separator, comma = decimal separator |

---

## 24. References (verify availability and license at time of use)

- CVL digit strings: https://cvl.tuwien.ac.at/research/cvl-databases/icdar2013-handwritten-digit-and-digit-string-recognition-competition/
- ORAND-CAR-2014 + CVL HDS (ICFHR 2014): https://www.orand.cl/icfhr2014-hdsr/
- Handwritten names (CC0): https://www.kaggle.com/datasets/landlord/handwriting-recognition
- CORD v2: https://huggingface.co/datasets/naver-clova-ix/cord-v2
- Base VLM: https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct
- Pretrained handwriting OCR: https://huggingface.co/microsoft/trocr-small-handwritten
- Kaggle Community Benchmarks: https://www.kaggle.com/docs/benchmarks
- AWS Free Tier terms: https://aws.amazon.com/free/terms
