# COCOK — Project Blueprint (v2.1)

```yaml
doc_id: cocok-blueprint
version: 2.2.0            # semver; bump on every accepted change to this file
status: proposed          # becomes approved-for-build when Arka accepts ADR-0003..0013 (or edits them)
owner: Arka               # human; final decision maker on every open question
created: 2026-10-01
updated: 2026-10-01
previous_version: docs/archive/BLUEPRINT-v2.0.0.md
language_policy: "Code, docs, commits in English. Domain terms stay Indonesian (see §23 Glossary). UI copy in Indonesian."
repo_location_of_this_file: docs/BLUEPRINT.md
companion_docs:
  checkpoints: docs/CHECKPOINTS.md        # HOW and IN WHAT ORDER to build (CP-00..CP-33, gates, debug playbooks)
  function_specs: docs/FUNCTION_SPECS.md  # WHAT each significant function must do (contracts, examples, tests)
  progress: docs/PROGRESS.md              # status board + per-checkpoint logs in docs/progress/
  tech_refresh: docs/TECH_REFRESH_2026-10.md
```

### Changelog v2.0.0 → v2.1.0 (all changes are backed by ADRs; ADR status = proposed until Arka accepts)

| § | Change | ADR |
|---|---|---|
| 0, 17, 18 | Checkpoint-driven delivery (CP-00..CP-33), executable gates, progress logs, 12-week calendar with buffer, cut line | 0013 |
| 2, 4.3, 5.6, 11 | τ chosen with a finite-sample guarantee (SGR / Clopper–Pearson); every metric reported with 95 % CI; T3 = 100 docs (30 calib / 70 test); replay-based eval gate | 0007 |
| 4.2, 8 | `photo_sim` on torchvision v2 + own ops (Albumentations archived; successor is AGPL) | 0009 |
| 5.1, 5.6, 16 | Grounding by aligning values to CPU OCR line boxes (RapidOCR); new signal `s_ocr_agree` | 0006 |
| 5.2, 5.3, 24 | Base VLM → Qwen3.5-2B (native multimodal); 16-bit LoRA (no QLoRA); transformers v5; PaddleOCR-VL-1.6 / GLM-OCR baselines | 0003 |
| 5.1, 15 | Prod digital route = PDF text layer (pypdfium2) first; Docling stays as baseline B4 and must earn its RAM | 0010 |
| 6, 8, 9, 12 | Redis + arq removed; Procrastinate (Postgres) queue; psycopg 3 single driver | 0004 |
| 6.1, 6.2 | LangGraph run ends at `decide`; review is a domain-FSM use case (no long-lived interrupts) | 0005 |
| 6.3, 6.4, 13, 15 | Opaque server-side sessions (no JWT), pwdlib argon2id, same-site domain topology | 0008 |
| 13, 15 | CI supply-chain hardening; native arm64 runners | 0011 |
| 6.4, 8, 9, 12, 16, 17 | Toolchain refresh (PG18, Python 3.13 runtime, Langfuse v4, MLflow 3, Next.js 16, Schemathesis, Google-style tested docstrings) and documented non-changes (mypy kept over ty beta, etc.) | 0012 |

**v2.2.0 (2026-10-01): workflow change (ADR-0014).** The AI implements every checkpoint, including the former
"human-owned" modules (now *learning-critical*); Arka brainstorms decisions, studies, tests and signs off each
checkpoint. §0, §19, §20 and CHECKPOINTS §0 updated.

**v2.1.1 (2026-10-01, CP-02):** §3.2 clarified — every `ExtractedDocument` field except `doc_type` is nullable;
requiredness is defined only by the per-doc_type table (it already was: e.g. `surat_jalan` has no `total_amount`).
§9 docstring convention: first line ends with `(FS-ID).` (pydocstyle D415).

Unchanged on purpose: goals (§1.1), non-goals (§1.2), headline metric definition (§2), data sources and
licenses (§4.1). (§20 changed in v2.2.0 — ADR-0014.)

---

## 0. Rules for AI agents reading this file

- This file is the **single source of truth (SSOT)** for *what* and *why*. `docs/CHECKPOINTS.md` is the SSOT for
  *order and acceptance*; `docs/FUNCTION_SPECS.md` is the SSOT for *function contracts*. Precedence when
  instructions conflict:
  1. Explicit instruction from Arka in the current session
  2. This blueprint
  3. Accepted ADRs in `docs/adr/`
  4. `docs/CHECKPOINTS.md`, then `docs/FUNCTION_SPECS.md`
  5. Agent judgment
- Keywords **MUST / MUST NOT / SHOULD / MAY** follow RFC 2119.
- Read order: §1–§3 (what and why) → §19 (your role brief) → §20 (ownership policy) → the **current checkpoint**
  in `docs/CHECKPOINTS.md` → the FUNCTION_SPECS entries that checkpoint lists → sections your role references.
- **Work only inside the current checkpoint.** Do not start work belonging to a later checkpoint; do not modify
  files outside the checkpoint's "Files" list without saying why in the PR.
- **A checkpoint is done only when its gate passes** (`make gate CP=NN`) and `make gates-upto CP=NN` is green.
- **Do not invent requirements.** If something is ambiguous or missing: propose 2–3 options with trade-offs, ask
  Arka, then record the decision as an ADR.
- Any change to architecture, data contracts, metrics, or this file → one PR that updates this file **and** adds an
  ADR, and bumps `version`.
- One concern per PR. Small PRs. No drive-by refactors in bug-fix PRs.
- Repo setup: this file at `docs/BLUEPRINT.md`; `AGENTS.md` at repo root (Claude Code reads `CLAUDE.md` → keep a
  one-line `CLAUDE.md` that says "See AGENTS.md").

---

## 1. Project identity

| Item | Value |
|---|---|
| Name | **Cocok** (Indonesian: "match") |
| One-liner | An evaluation-first document reconciliation agent for Indonesian back-offices that **knows when not to trust itself**. |
| Problem | Small businesses receive mixed documents: digital invoices and tax invoices (faktur), photographed delivery notes (surat jalan), handwritten notes and receipts (nota, kwitansi). Manual data entry and matching against purchase orders is slow and error-prone. Common OCR tools degrade on low-quality or handwritten documents and silently output wrong values. |
| Core idea | Extract → validate deterministically → score calibrated confidence → **automate only when safe (with a statistical guarantee)**, route everything else to a human with grounded evidence (field ↔ location on the image). |
| Default persona | Back-office admin of a building-materials store (toko bangunan) or small distributor that receives goods from many small suppliers. *(Open decision D1.)* |
| Portfolio purpose | Prove, end-to-end: dataset creation, model training (from scratch + fine-tuning), LLM/VLM integration, evaluation and calibration, production engineering, full-stack delivery. |
| Target employers | Document-AI / AP-automation teams (e.g., Indonesian spend-management and OCR companies), AI-engineering roles requiring RAG/agents/eval/production (Indonesia, Singapore, remote). |

### 1.1 Goals
- **G1** Publish a dataset that does not exist publicly: Indonesian nota/kwitansi-style documents with field-level labels, including real human handwriting tiers.
- **G2** Benchmark extraction strategies (OCR pipeline, zero-shot API VLM, zero-shot small VLM, fine-tuned small VLM) on cost, latency, and accuracy.
- **G3** Train two models: an amount reader (from-scratch CRNN vs fine-tuned TrOCR experiment) and a LoRA-fine-tuned small VLM.
- **G4** Calibrated confidence with abstention; report a risk–coverage curve, a **certified** operating point, and an ablation study.
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
  report_variants:                      # v2.1 (ADR-0007): how it is reported, not what it means
    empirical: "max coverage with empirical risk <= 1% on the test tier"
    certified: "coverage on the test tier at the tau selected on calib by SGR (doc-level Clopper-Pearson UCB <= 1%, delta=0.05)"
  visualization: risk_coverage_curve
metrics:
  - id: field_accuracy
    definition: "Exact match after normalization, per field, per doc_type, per test_tier."
  - id: amount_exact_match
    definition: "Exact match of total_amount (critical field), per test_tier."
  - id: calibration_ece
    definition: "Expected Calibration Error of per-field confidence (15 equal-width bins), plus reliability diagram."
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
reporting_rules:                        # v2.1 (ADR-0007)
  intervals: "Every proportion carries a 95% Clopper-Pearson CI; field-level metrics and ECE carry a 95% document-cluster bootstrap CI (2000 resamples)."
  minimum_n_statement: "If a tier/doc_type cell has n < 30 documents, show the number with its CI and the label 'indicative'."
  certification_note: "Certifying risk <= 1% needs >= 299 auto-approved calib documents with 0 errors at one fixed tau (473 with 1 error); with SGR's Bonferroni split over the threshold search it rises to ~530-540. If not reached, report certified coverage = 0 and say so."
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
  vendor_nitku: str|null       # 22 digits = 16-digit NPWP + 6-digit place code (000000 = head office)
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
  bbox: [page, x0, y0, x1, y1] | null   # page-normalized coordinates in [0,1]; origin top-left (v2.1: fixed convention)
  bbox_source: enum[text_layer, ocr_alignment, extractor, none]   # v2.1 (ADR-0006)
  signals: dict                # per-signal values used by the calibrator
Money: { amount_idr: int }     # integer rupiah, never float
```

**Required fields per doc_type** (used by the abstention policy; v2.1 makes this explicit). In code every field
except `doc_type` is nullable; this table is the only source of requiredness (`REQUIRED_FIELDS`, FS-CM-03):

| doc_type | required |
|---|---|
| invoice | vendor_name, doc_number, doc_date, total_amount, line_items (≥1) |
| nota | vendor_name, doc_date, total_amount, line_items (≥1) |
| kwitansi | payer_name, total_amount, amount_in_words, doc_date |
| surat_jalan | vendor_name, doc_number, doc_date, line_items (≥1, qty+description) |
| purchase_order | (structured input; not extracted) |

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
| `own_hand` | Arka's own handwriting (2–3 deliberate styles) | Full Indonesian nota/kwitansi/surat jalan | Own | Tier T3 (calib + test); publish |

**Prohibited data:** web-scraped images; real third-party documents in any public artifact; AI-generated handwriting in **any test tier**.

**Third-party model providers (v2.1):** documents sent to a provider whose free tier may use content for product
improvement (e.g., Gemini API free tier, Kaggle-hosted model access) MUST be synthetic or from `names`/`cvl_hds`/
`own_hand`. Never `orand_car` (ND license) and never redacted personal documents.

### 4.2 Scenario generator (ground truth is created first, documents are rendered from it)
- Generates fictional transactions: vendor, items, quantities, prices, totals, terbilang, dates, NPWP (15-digit legacy and 16-digit formats), NITKU, PO references.
- Planted perturbations with labels: total ≠ sum of lines, terbilang ≠ total, qty mismatch vs PO, price mismatch vs PO, duplicate doc number, legacy NPWP format, missing required field.
- Renderers:
  - `digital`: HTML template → PDF (text layer present; WeasyPrint or headless Chromium/Playwright).
  - `handwriting_like`: handwriting fonts + stroke-width/jitter augmentation (training only).
  - `composite`: paste real handwritten crops (`names`, `cvl_hds`) into kwitansi/nota templates; record bbox per field.
  - `photo_sim`: perspective, blur, shadow, low light, JPEG compression, paper texture, crumple — **torchvision.transforms.v2 + own NumPy/OpenCV ops; geometric ops transform GT bboxes with the same matrix** (ADR-0009).
- Every rendered item ships with JSON ground truth + per-field bbox from the renderer.
- Deterministic: seeded RNG (`numpy.random.Generator(PCG64(seed))`, one child seed per item); generator config versioned (`datagen/config/*.yaml`); generator version and every augmentation's parameters recorded in manifests.
- All generated identifiers (NPWP, NIK, NITKU, phone numbers) MUST be random and fictional; dataset card states this explicitly.
- **T3 workflow (v2.1):** the generator prints a *scenario sheet*; Arka hand-writes the document from it. Ground truth already exists → only the `total_amount` bbox needs manual annotation (Label Studio or a 50-line script). This removes most labeling work.

### 4.3 Test tiers

| Tier | Content | Writers | Measures |
|---|---|---|---|
| T0 | Held-out synthetic (all doc types) | n/a | Sanity, regression |
| T1 | `cvl_hds` test split + `orand_car` test split, as-is | Hundreds of real writers | Amount reader |
| T2 | Composite kwitansi/nota: templates + `names` test crops + `cvl_hds` test digit strings | Hundreds of real writers | Document-level extraction on real strokes |
| T3 | Arka's handwriting: **100** Indonesian documents, 2–3 styles, varied photo conditions; split **30 `T3-calib` / 70 `T3-test`** stratified by style × doc_type (v2.1, ADR-0007) | 1 person, multiple styles | Indonesian-specific end-to-end (terbilang, item names, formats); calibration under real-handwriting shift |

Known limitation (MUST appear in README and dataset card): Indonesian-word handwriting variety is limited to one person's styles in T3.

### 4.4 Splits and leakage rules (MUST)
- Training uses only: `synth` train split, `names` train split, `cvl_hds` train split.
- Calibration fitting uses a dedicated **calib** split: synthetic val (≥ 1 500 docs) + a fixed subset of T2 marked `calib` (≥ 300 docs) + `T3-calib` (30 docs). Calib items MUST NOT appear in reported test results.
- No test-tier item (by sha256 and by source id) may appear in any training or calibration set. A CI job (`data-leakage-check`) MUST fail on overlap.
- Source crops (e.g., a `cvl_hds` digit string) used inside T2-calib composites MUST be excluded from T1 and T2-test reporting.
- Report metrics on T0, T1, T2-test, T3-test separately. Never pool tiers in the headline without also showing per-tier numbers.

### 4.5 Storage and versioning
- Raw data is **not** stored in git. Use object storage or a Hugging Face dataset repo (private until license review passes).
- `data/manifests/*.parquet` in git: `item_id, sha256, source_id, source_item_id, license, split, tier, doc_type, generator_version, augment_params_json, created_at`.
- Dataset releases are tagged (`cocok-docs-v0.1`, …) with a dataset card (`docs/DATASET_CARD.md`).
- A publish script MUST refuse to upload items whose license is `CC-BY-NC-ND` or whose source is not publishable.

### 4.6 Privacy and ethics
- Own documents (e.g., personal receipts) are redacted before storage; never published unredacted.
- Any helper writer (optional) signs a short written consent for publication of their handwriting.
- Synthetic content is fictional; no real persons or businesses are implied.

---

## 5. Model plan

### 5.1 Routing (per document)
1. Detect input kind: PDF with a usable text layer (≥ N chars per page, configurable) → `digital` route; image or scanned PDF → `visual` route.
2. `digital` (prod default, ADR-0010): `pypdfium2` text + character boxes → "layout text" → LLM structuring into `ExtractedDocument`. Docling is benchmarked as B4 and adopted in prod only if it wins **and** fits the memory budget.
3. `visual`: primary VLM extraction (fine-tuned small VLM **only if** it wins the benchmark; otherwise best API VLM).
4. **Grounding (ADR-0006):** run RapidOCR (ONNX, CPU) on visual pages; align each extracted value to OCR lines → `bbox` + `s_ocr_agree`. Digital route uses text-layer boxes.
5. **Always** run the amount reader on the grounded `total_amount` crop as an independent second read.
6. Deterministic validators and the confidence model run on every route.

### 5.2 Baselines (Milestone A)
- **B1a** OCR pipeline: PaddleOCR-VL-1.6 → text LLM structuring.
- **B1b** GLM-OCR with a key-information-extraction prompt → JSON (single model).
- **B2** Zero-shot API VLMs. Kaggle Community Benchmarks **supports image input** (`kaggle-benchmarks` SDK); use it for benchmark runs if terms allow (D4). Otherwise OpenAI (remaining credits), Bedrock (AWS credits), or Gemini free tier (**synthetic data only**). Record exact model id and date for every run.
- **B3** Zero-shot small open VLM: `Qwen/Qwen3.5-2B`, non-thinking mode, pinned revision.
- **B4** Digital PDFs: Docling (latest 2.x) **and** `pypdfium2` text layer → LLM; record `peak_rss_mb`.
- All baselines run through the same eval harness and the same normalization code.

### 5.3 Fine-tuned VLM (Milestone B)
- Base: `Qwen/Qwen3.5-2B` (native multimodal, Apache-2.0). Record exact HF revision hash. (ADR-0003)
- Method: **16-bit LoRA** via Unsloth + TRL (QLoRA is explicitly not recommended for Qwen3.5 by Unsloth); vision layers frozen in v1; output = JSON matching §3.2 schema; loss on assistant tokens only.
- Hardware note: Kaggle T4 has no bf16 → fp16 with loss scaling; mandatory 50-step smoke run (finite, decreasing loss) before full training. Qwen3.5 custom Triton kernels compile slowly on T4 — expected.
- Library pins: `transformers>=5,<6`, `peft`, `trl`, `unsloth` pinned to exact versions in the Kaggle notebook.
- Training data: `synth` train split (+ composites built from train splits only).
- Compute: Kaggle T4 (verify current weekly GPU quota in account settings at CP-00) → fallback Modal monthly free credits (L4/A10G, bf16) → RunPod only if > 16 GB VRAM is required (hard cap: $10 total).
- Deliverables: adapter on HF Hub, `docs/MODEL_CARD.md` section, MLflow run, Kaggle training notebook.
- Adoption rule: use as primary `visual` extractor only if it beats the best zero-shot route on `automation_rate_at_1pct` (certified variant), or matches it at materially lower cost/latency. Otherwise document "fine-tuning not worth it for this task" with evidence — this is a valid outcome.

### 5.4 Amount reader experiment (Milestone B)
- **Option A — from scratch:** CRNN + CTC in PyTorch. Pretrain on `names` train split; fine-tune on synthetic Rupiah amount crops + `cvl_hds` train split. Charset: digits, `.`, `,`, `-`, `R`, `p`, space.
- **Option B — pretrained:** `microsoft/trocr-small-handwritten` fine-tuned on the same data.
- Select the winner by exact match on T1; report both with CIs, including training cost and inference latency on CPU.
- The selected model is exported to **ONNX** and runs on CPU via `onnxruntime` in production (must fit the small server). ONNX parity test: max |Δlogit| < 1e-3 vs PyTorch on 100 crops.

### 5.5 Deterministic components (no ML; LEARNING-CRITICAL, see §20; contracts in FUNCTION_SPECS §2)
- `terbilang`: Indonesian number words ↔ integer (handles "se-", "belas", "puluh", "ratus", "ribu", "juta", "miliar", "triliun", "rupiah", common misspellings such as "milyar", glued words such as "duapuluh").
- `money`: parse/format `Rp 1.250.000,-`, `1.250.000`, `Rp1250000`, `500rb`, `1,25 jt` etc. → integer rupiah.
- `dates`: Indonesian month names (incl. old spellings "Pebruari", "Nopember") and numeric D/M/Y formats → ISO date. Never M/D/Y.
- `npwp`: normalize and validate. 16-digit NPWP; legacy 15-digit NPWP → prefix `0`; personal NPWP equals NIK (16 digits); NITKU = 22 digits = 16-digit NPWP + 6-digit place code (`000000` = head office). Formatting characters stripped. Structural validation only (no unpublished checksum).
- `arithmetic`: line_total = qty × unit_price; subtotal = Σ line_total; total = subtotal + tax (tolerances from `rules/tolerances.yaml`).
- `tax`: rates and bases loaded from `rules/tax.yaml` with effective dates. **MUST NOT hardcode VAT rates.** State verified 2026-10-01 (re-verify when writing the file): under PMK 131/2024 (effective 2025-01-01) the PPN rate is 12 %; for non-luxury goods the tax base is *DPP nilai lain* = 11/12 × price, so the effective rate is 11 %; luxury goods (PPnBM objects) use 12 % on the full price. Non-PKP small suppliers issue no PPN at all (tax_amount = null). Rounding mode is a rule-file field, not code.

### 5.6 Confidence and abstention (LEARNING-CRITICAL, see §20; contracts in FUNCTION_SPECS §3)
- Per-field signals: primary model score (token log-prob if available, else self-consistency over N=2–3 samples on hard cases), agreement between primary and amount reader, amount reader's own sequence probability, terbilang ↔ amount agreement, validator pass/fail, cross-field arithmetic consistency, **OCR-alignment similarity `s_ocr_agree` (v2.1)**, vendor-memory agreement (when available). Missing signals are encoded as value 0 + `is_missing` indicator, never silently imputed.
- Calibrator: logistic regression (default) or isotonic regression, **fit offline** in `ml/calibrate` on the **calib** split; selection by log-loss under 5-fold CV on calib; serialized as JSON (coefficients or isotonic breakpoints; no pickle) with a version; **applied at runtime** by a pure function in `core/confidence` (no scikit-learn in production).
- Policy: a document is auto-approved only if every required field ≥ τ, no blocking validator fails, and match status permits. **τ is selected by SGR** (ADR-0007): the lowest τ whose document-level Clopper–Pearson UCB of error among auto-approved calib docs ≤ 1 % at δ = 0.05 (Bonferroni over binary-search steps). τ is stored in `rules/confidence.yaml` with a version, the calib manifest hash, and the achieved UCB.
- Reports: risk–coverage curve, reliability diagram, ECE (with CI), certified vs empirical operating point, ablation (remove each signal; especially the amount reader; and "GT bbox vs aligned bbox").

### 5.7 Vendor memory (Milestone C, SHOULD)
- Human corrections are stored and keyed by normalized vendor NPWP, then vendor name.
- Retrieval: exact key lookup first; fuzzy name match (`pg_trgm`) second; embeddings only if both fail and evidence shows benefit. Do not use vectors where a key lookup works.
- Uses: few-shot examples for the API route; automatic regression test cases.
- Measure before/after on a repeat-vendor subset.

### 5.8 Experiment tracking
- MLflow 3.x (local/sqlite backend; artifacts to object storage). Every run logs: git SHA, data manifest version, config, metrics, model artifacts, HF revision hashes, library versions.
- Notebooks are for exploration only. Training/eval code lives in `packages/ml`; Kaggle notebooks install the package at a pinned commit and call its CLI.

---

## 6. System architecture

```
[Next.js 16 web (Vercel, app.<domain>)] --HTTPS, same-site cookies--> [Caddy (api.<domain>)] --> [FastAPI api]
                                                                                                    |
                                                          (enqueue in the same DB transaction)      |
                                                                                                    v
                                          [PostgreSQL 18: app tables + procrastinate jobs + LangGraph checkpoints]
                                                    ^                                               |
                                                    |                                               v
                                          [Object storage: S3 or local]       [Worker: Procrastinate → LangGraph pipeline]
                                                                                   +--> Model adapters: API VLM | local VLM | OCR (RapidOCR) | amount reader (ONNX)
                                                                                   +--> Langfuse v4 (OTel), OpenTelemetry, structlog
```
(v2.1: no Redis — ADR-0004.)

### 6.1 Pipeline (LangGraph 1.x, Postgres checkpointer; thread id = `{document_id}:{pipeline_version}`)
`ingest → detect_input_kind → classify_doc_type → route → extract → ground → read_amount → validate → score_confidence → match_against_po → decide → persist → emit_events`
- `decide` → `AUTO_APPROVED` or `NEEDS_REVIEW`. **The graph run ends after `persist`/`emit_events`** (ADR-0005). Human review, approval, rejection and posting are service-layer use cases on the domain FSM — no long-lived interrupts.
- The checkpointer provides crash-resume within a run (a paid model call is never repeated after its node completed).
- Every node: typed input/output (Pydantic), idempotent, timeout, retries with exponential backoff + jitter on retryable errors only.
- Pipeline version string recorded on every run.

### 6.2 Document status state machine (enforced in `core`; invalid transitions raise a domain error; the ONLY lifecycle authority)
```
UPLOADED → QUEUED → PROCESSING → EXTRACTED → {AUTO_APPROVED | NEEDS_REVIEW}
NEEDS_REVIEW → {APPROVED | REJECTED}
AUTO_APPROVED | APPROVED → POSTED
PROCESSING → FAILED (retry_count, reason) → QUEUED (manual or auto retry, max 3)
```

### 6.3 API (REST, `/api/v1`, OpenAPI is the contract)
- Auth (v2.1, ADR-0008): `POST /auth/login` · `POST /auth/logout` · `GET /auth/me` · `GET /auth/csrf`
- `POST /documents` (multipart; `Idempotency-Key` header) → `202 {document_id, job_id}`
- `GET /documents/{id}` · `GET /documents/{id}/extraction` · `GET /documents/{id}/file` (short-TTL presigned URL)
- `PATCH /documents/{id}/fields/{field}` (correction, with reason)
- `POST /documents/{id}/approve` · `POST /documents/{id}/reject` · `POST /documents/{id}/reprocess` (new pipeline run)
- `GET /review-queue?sort=confidence&cursor=…`
- `GET|POST /purchase-orders` · `GET /documents/{id}/match`
- `GET /metrics/summary` (admin)
- `GET /healthz` (liveness) · `GET /readyz` (DB, storage, worker heartbeat < 60 s)
- Errors: RFC 9457 `application/problem+json`. Pagination: cursor-based.

### 6.4 Data model (PostgreSQL 18; UUIDv7 primary keys — generated in app via `IdGenerator` port, DB default `uuidv7()`; `timestamptz` UTC)
- `users`, `roles`, `user_roles`, **`sessions`** (id_hash, user_id, created_at, last_seen_at, expires_at, revoked_at, ua_hash)
- `vendors` (normalized_npwp unique nullable, name, aliases)
- `purchase_orders`, `po_lines`
- `documents` (sha256 unique, doc_type, status, storage_key, uploaded_by, pipeline_version)
- `extraction_runs` (document_id, route, model_id, model_revision, adapter_version, prompt_id, prompt_version, rules_version, code_sha, latency_ms, cost_usd, raw_output jsonb, peak_rss_mb)
- `extracted_fields` (run_id, field, value_raw, value_normalized jsonb, confidence, bbox, bbox_source, signals jsonb)
- `corrections` (field_id, old_value, new_value, user_id, reason)
- `match_results` (document_id, po_id, status, discrepancies jsonb)
- `audit_log` (append-only: actor, action, entity, before, after, at)
- `worker_heartbeats` (worker_id, seen_at) — if the pinned Procrastinate version lacks an equivalent
- Procrastinate tables (`procrastinate_*`) and LangGraph checkpoint tables live in a separate schema (`queue`, `lg`).
- Every prediction is traceable to (code SHA, model + revision, adapter, prompt version, rules version, pipeline version).

---

## 7. Repository structure (monorepo)

```
cocok/
├── AGENTS.md                      # read docs/BLUEPRINT.md first; follow §20; work in the current checkpoint only
├── CLAUDE.md                      # one line: "See AGENTS.md"
├── README.md
├── Makefile                       # setup, lint, type, test, gate CP=NN, gates-upto CP=NN, eval
├── pyproject.toml                 # uv workspace root; requires-python >=3.12; .python-version = 3.13
├── apps/
│   ├── api/src/cocok_api/
│   │   ├── main.py                # app factory only
│   │   ├── deps.py                # composition root: wires ports → adapters
│   │   ├── routers/               # HTTP only: parse, authz, call service, map errors
│   │   ├── services/              # use-cases orchestrating core + ports (incl. review/approve via FSM)
│   │   ├── schemas/               # request/response DTOs
│   │   ├── auth/                  # pwdlib hashing, sessions, CSRF, RBAC guards
│   │   └── middleware/            # request id, logging, security headers, rate limit
│   ├── worker/src/cocok_worker/
│   │   ├── bootstrap.py           # composition root for worker
│   │   ├── graph.py               # LangGraph wiring only
│   │   ├── nodes/                 # one file per pipeline node
│   │   └── tasks.py               # Procrastinate task entrypoints
│   └── web/                       # Next.js 16 (TypeScript), pnpm
├── packages/
│   ├── core/src/cocok_core/       # DOMAIN: pure Python. No I/O. No framework imports.
│   │   ├── models/                # entities, value objects (Money, Npwp, DocumentStatus FSM)
│   │   ├── validation/            # npwp, money, terbilang, dates, arithmetic, tax   [LEARNING-CRITICAL]
│   │   ├── matching/              # po_matching, tolerances                          [LEARNING-CRITICAL]
│   │   ├── confidence/            # signals, apply calibrator (pure), decide policy  [LEARNING-CRITICAL]
│   │   ├── ports/                 # Protocols: Extractor, AmountReader, Ocr, Storage, Repository, LLMClient, JobQueue, Clock, IdGenerator
│   │   └── errors.py
│   ├── adapters/src/cocok_adapters/
│   │   ├── db/                    # SQLAlchemy models + repositories (psycopg 3)
│   │   ├── queue/                 # procrastinate.py
│   │   ├── storage/               # s3.py, local.py (same contract tests)
│   │   ├── llm/                   # bedrock.py, openai.py, gemini.py, kaggle_proxy.py
│   │   ├── vlm/                   # local_qwen.py (eval/bench only)
│   │   ├── ocr/                   # rapidocr.py (prod), pdf_text.py (pypdfium2), docling.py, paddle_vl.py (eval)
│   │   ├── grounding/             # align.py (value ↔ OCR line)                       [ADR-0006]
│   │   └── amount_reader/         # onnx_reader.py (CRNN or TrOCR export)
│   └── ml/src/cocok_ml/           # training + eval; NEVER imported by api/worker at runtime
│       ├── datagen/               # scenario generator, renderers, photo_sim
│       ├── train/crnn/            # model + training loop                            [LEARNING-CRITICAL]
│       ├── train/trocr/  train/vlm_lora/
│       ├── eval/                  # runner, replay, reports; metrics/               [metrics LEARNING-CRITICAL]
│       └── calibrate/             # fit_calibrator, select_threshold_sgr (offline)   [LEARNING-CRITICAL]
├── prompts/                       # *.md with front matter: id, version, model_family
├── rules/                         # tax.yaml, tolerances.yaml, confidence.yaml (versioned, effective dates)
├── data/manifests/                # parquet manifests; no raw data
├── evals/                         # eval configs, baseline.json, gate.yaml, cache/ (replay outputs, git-ignored or LFS)
├── migrations/                    # Alembic
├── scripts/gates/                 # cp00.sh … cp33.sh (one executable gate per checkpoint)
├── infra/
│   ├── docker/                    # Dockerfiles (multi-stage, non-root)
│   ├── compose/                   # compose.dev.yml, compose.prod.yml (memory limits)
│   ├── caddy/Caddyfile
│   └── scripts/                   # deploy.sh, rollback.sh, backup.sh, restore.sh
├── docs/                          # see §17
└── .github/workflows/             # ci-python.yml, ci-web.yml, eval-gate.yml, data-checks.yml, security.yml, checkpoint-gates.yml, deploy.yml
```

### 7.1 Layering rules (MUST; enforced by `import-linter` in CI)
- `core` imports nothing from `adapters`, `api`, `worker`, `ml`. No network, disk, DB, or clock access in `core` (time comes through the `Clock` port, IDs through `IdGenerator`). Allowed third-party imports in `core`: `pydantic`, `rapidfuzz` (pure functions) — anything else needs an ADR.
- `api` and `worker` depend on `core` ports; concrete adapters are injected only in `deps.py` / `bootstrap.py`.
- `ml` may import `core` (to reuse validators and terbilang); `api`/`worker` MUST NOT import `ml`.
- Nothing imports `redis` or `arq` (ADR-0004).
- Soft limits (ruff-enforced where possible): file ≤ 300 lines, function ≤ 50 lines, cyclomatic complexity ≤ 10. Exceptions require a one-line justification comment.

---

## 8. Tech stack (pin all versions in lockfiles; upgrade via Dependabot PRs; verified 2026-10-01 — see docs/TECH_REFRESH_2026-10.md)

```yaml
python: "3.13 runtime (.python-version); requires-python >=3.12 (Kaggle compatibility)"
python_tooling: [uv (workspaces), ruff (incl. D/pydocstyle google), mypy (strict for core + adapters), import-linter, pytest, pytest-asyncio, hypothesis, testcontainers, schemathesis, coverage, pre-commit]
backend: [fastapi, pydantic v2, pydantic-settings, sqlalchemy 2 (async) + psycopg 3, alembic, procrastinate 3.x, langgraph 1.x + langgraph-checkpoint-postgres, httpx, tenacity, structlog, opentelemetry, langfuse sdk v4, pwdlib[argon2], uuid-utils]
ml: [torch, transformers v5, peft, trl, unsloth (Kaggle/Modal only), accelerate, datasets, torchvision (transforms.v2), opencv-python-headless, scikit-learn, scipy, mlflow 3.x, docling (eval), paddleocr / PaddleOCR-VL-1.6 (eval), glm-ocr (eval), rapidocr + onnxruntime (prod), pypdfium2, onnx]
web: [next.js 16 (app router, turbopack, proxy.ts), react 19.2, typescript strict, tailwind v4, shadcn/ui, tanstack query v5, openapi-typescript + openapi-fetch, zod v4, react-pdf/pdf.js, vitest, playwright, eslint (flat config, CLI) or biome, prettier, pnpm]
infra: [docker (multi-arch arm64+amd64 via native runners), docker compose, caddy 2, postgres 18 (+pgvector only if embeddings adopted, +pg_trgm), aws ec2 graviton (t4g.small), ecr, ssm parameter store, s3, vercel, github actions (OIDC to AWS)]
security_tooling: [gitleaks, pip-audit, pnpm audit, trivy (SHA-pinned) or grype, zizmor, step-security/harden-runner, dependabot, pip-licenses]
observability: [langfuse cloud hobby (sdk v4, OTel-native), opentelemetry (GenAI semconv pinned; experimental), sentry (free tier, optional)]
docs: [markdown in repo (source of truth), optional zensical site with built-in mkdocstrings support]
embeddings_if_needed: [voyage-4 family (free token allowance) or local open-source model]
```

---

## 9. Engineering standards (MUST)

- **Typing:** all public functions typed; `mypy --strict` on `core` and `adapters`.
- **Docstrings (v2.1):** Google style on every public function/class in `core`, `adapters`, `api/services`, `ml/eval`; `ruff` `D` rules enforce presence; `core` docstrings contain runnable `Examples:` executed by `pytest --doctest-modules packages/core`. Content follows the FUNCTION_SPECS entry (the docstring's first line ends with its FS-ID, e.g. `"""Parse Indonesian rupiah text (FS-CV-01).`).
- **Errors:** typed domain errors in `core/errors.py` (`DomainError` → `ValidationError`, `InvalidTransition`, `RetryableError`, …); no bare `except`; API maps errors to problem+json; never return stack traces to clients.
- **Logging:** structlog JSON to stdout; every line carries `request_id` / `job_id` / `document_id`; a redaction processor removes secrets and personal data (NPWP/NIK masked to last 4).
- **Config:** pydantic-settings, 12-factor; `.env.example` documents every variable; app fails fast at startup on invalid config.
- **API contract:** OpenAPI generated from FastAPI; TypeScript client generated in CI; breaking changes require `/api/v2`; Schemathesis runs against the spec in CI.
- **DB migrations:** Alembic only; every migration has a working downgrade; CI runs upgrade → downgrade → upgrade on an empty DB; breaking schema changes use expand → migrate → contract across separate releases.
- **Jobs:** idempotent (key = document sha256 + pipeline version, enforced by Procrastinate queueing lock); enqueued in the same transaction as the status change; retries only on `RetryableError`; failures land in `FAILED` with a reason.
- **External calls:** explicit timeouts on every call; per-route fallback; cost recorded per call; provider-native structured output (JSON schema) where available, always re-validated with Pydantic.
- **Prompts:** files in `prompts/` with `id` and `version`; version logged on every LLM call; any prompt change triggers the live eval gate.
- **Business rules:** data in `rules/*.yaml`, schema-validated at startup; never hardcoded.
- **Money:** integer rupiah only; never floats. `Decimal` for quantities.
- **Git:** trunk-based, short-lived branches (`cp/NN-slug`), PR required for `main`, conventional commits, squash merge, semver tags + checkpoint tags `cp-NN`, `CHANGELOG.md` (Keep a Changelog).
- **Code review checklist (every PR):** tests added/updated · layering respected · no secrets · migrations reversible · docs/ADR/FUNCTION_SPECS updated if behavior changed · checkpoint gate green · `ai-assisted` label if applicable.

---

## 10. Testing strategy and bug-fix protocol

- **Unit (core):** fast, no I/O; coverage gate ≥ 90 % lines on `core`.
- **Doctests (core):** every `Examples:` block in a `core` docstring is executed.
- **Property-based (Hypothesis):** terbilang round-trip (int → words → int); money parse ↔ format round-trip; NPWP normalization idempotent; arithmetic invariants; FSM: random event sequences never reach an undefined state.
- **Contract tests:** one shared suite per port, run against every adapter (e.g., `Storage` against s3 (MinIO/LocalStack container) and local; `LLMClient` against recorded fixtures; `JobQueue` against Procrastinate on Postgres).
- **Integration:** adapters with testcontainers (Postgres 18); LLM adapters use recorded responses (no live calls in CI except the live eval gate).
- **API fuzz:** Schemathesis against the OpenAPI schema (no 5xx, problem+json on errors).
- **Golden tests:** fixed documents with expected deterministic outputs (validators, matching, grounding) to catch regressions.
- **E2E:** API flow test; Playwright critical path upload → review → correct → approve.
- **Checkpoint gates:** `scripts/gates/cpNN.sh`, cumulative (`make gates-upto CP=NN`) — see `docs/CHECKPOINTS.md` §0.
- **Overall coverage gate:** ≥ 75 %.
- **Bug-fix protocol (MUST):** reproduce → write a failing test → minimal fix → full suite green → `docs/FAILURE_LOG.md` entry if user-visible or model-related (date, symptom, root cause, fix, test added, checkpoint where introduced) → no unrelated changes in the same PR.
- **Flaky tests are bugs:** quarantine with a label and open an issue the same day.

---

## 11. Evaluation harness and CI eval gate

- CLI: `cocok-eval run --route <route_id> --tiers T0,T1,T2,T3 --out evals/results/<run_id>/` and `cocok-eval replay --from <run_id> --tiers T0,T2` (re-score cached raw outputs with current rules/validators/confidence; zero API cost).
- Outputs: `metrics.json` (every metric with CI), `report.md`, plots (risk–coverage with empirical and certified points, reliability diagram, per-field accuracy), per-item predictions + raw outputs (cache) for error analysis and replay.
- Same normalization code (`core.validation`) for every route, so comparisons are fair.
- **Eval gate (v2.1, ADR-0007):**
  - **Replay gate** — PRs touching `rules/`, `core/validation`, `core/confidence`, `core/matching`: replay on full T0 + T2-test; fail if certified automation rate decreases, or any critical-field accuracy's CI upper bound falls below the baseline point estimate.
  - **Live gate** — PRs touching `prompts/` or `adapters/llm|vlm|ocr|amount_reader|grounding`: paired run on a fixed 30-doc set; fail if ≥ 2 more documents are wrong than the baseline run (count-based); cost cap $0.50 (configurable).
  - Thresholds in `evals/gate.yaml`. Updating `evals/baseline.json` requires an explicit PR with justification.
- Full evaluation: manual or scheduled; results summarized in `docs/EVAL_REPORT.md` with dataset version, model revisions, prompt versions, code SHA.

---

## 12. Observability

- **Traces:** OpenTelemetry spans for API requests and every pipeline node; LLM/VLM calls traced in Langfuse (SDK v4 is OTel-native → same trace context) with prompt id/version, model, tokens, cost, latency, route. GenAI semantic conventions are still experimental → pin the semconv version.
- **Logs:** structlog JSON → stdout; Docker log rotation enabled.
- **Errors:** Sentry for api, worker, web (free tier; optional but recommended).
- **Product metrics** (computed from DB, shown on `/dashboard`): documents processed, auto-approve rate, abstain rate, correction rate per field, cost per doc, p95 latency per route, queue depth (Procrastinate), failure rate.
- **Health:** `/healthz`, `/readyz`; worker heartbeat row in Postgres.
- **Alerts (minimal, free):** scheduled GitHub Action uptime check; failure rate above threshold; daily LLM spend above cap; AWS Budget alarms; container memory > 90 % of limit.

---

## 13. Security (baseline: OWASP ASVS Level 1 + OWASP Top 10 for LLM Applications)

**Authentication and authorization (v2.1, ADR-0008)**
- Passwords hashed with argon2id via `pwdlib` (`PasswordHash.recommended()`), rehash on login when parameters change.
- **Opaque server-side sessions**: 256-bit random id in an httpOnly, Secure, SameSite=Lax, host-only cookie; DB stores only its SHA-256; absolute lifetime 7 d, idle 12 h; id rotated on login and privilege change; all sessions revoked on password change.
- CSRF: double-submit token + `Origin` check on every cookie-authenticated mutation.
- RBAC roles: `viewer`, `staff`, `manager`, `admin`. Approving documents requires `manager`. Role changes are audited and revoke the user's sessions.
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
- **CI supply chain (v2.1, ADR-0011):** every `uses:` pinned to a full commit SHA; `permissions: {}` by default; `zizmor` audit; `harden-runner` egress audit; secrets only in jobs that need them; never `pull_request_target`.
- Containers: multi-stage builds, minimal base images, non-root user, read-only root filesystem where possible, memory limits; Trivy/Grype scan in CI fails on fixable HIGH/CRITICAL.
- Dependencies: Dependabot (ML deps monthly), pip-audit, pnpm audit, `pip-licenses` (no AGPL/GPL in runtime or `ml` extras) in CI.
- Network: HTTPS only (Caddy automatic TLS); security headers (HSTS, CSP, X-Content-Type-Options, Referrer-Policy, frame-ancestors); CORS allowlist (`https://app.<domain>` with credentials); rate limits on auth and upload endpoints; DB never exposed publicly; server access via SSM Session Manager instead of open SSH.
- Database: application role with least privilege; separate migration role.
- `audit_log` is append-only (no UPDATE/DELETE grants for the app role).
- `SECURITY.md` describes how to report vulnerabilities.
- Threat model (STRIDE-lite) reviewed at the end of each milestone.

---

## 14. Data management, backup and recovery

- **PostgreSQL:** nightly `pg_dump -Fc` → encrypted (age) → S3 bucket with versioning and lifecycle (7 daily, 4 weekly, 3 monthly). Weekly encrypted copy to a second location outside the primary cloud. (The queue and checkpoints are in the same database → one backup covers all state.)
- **Object storage:** bucket versioning on; lifecycle rules purge demo uploads after the retention period.
- **Pre-deploy backup:** `deploy.sh` takes a backup before running migrations.
- **Targets:** RPO ≤ 24 h, RTO ≤ 2 h.
- **Restore drill (MUST):** monthly scripted restore into a scratch database + smoke test; result logged in `docs/RUNBOOK.md`. A backup that has never been restored does not count as a backup.

---

## 15. Deployment, environments and portability

**Environments:** `local` (docker compose) · `prod` (single EC2 `t4g.small` + docker compose + Caddy at `api.<domain>`) · web on Vercel at `app.<domain>`; preview deployments per PR talk to a demo API with sandbox users only (ADR-0008).

**Memory budget on `t4g.small` (2 GB) (v2.1):** Postgres ≤ 512 MB, API ≤ 256 MB, worker ≤ 1 GB (RapidOCR + ONNX amount reader; no torch in the worker image), Caddy ≤ 64 MB; 1 GB swap file as safety net. Gate: total RSS < 1.6 GB idle, no OOM over a 10-document smoke run.

**CI/CD (GitHub Actions)**
- On PR: lint, typecheck, import-linter, unit + doctest + integration tests, migration up/down test, data-leakage check, security scans (incl. zizmor), Docker build, web tests, Schemathesis, checkpoint gates, eval gate (when triggered).
- On merge to `main`: build multi-arch images on native amd64 + arm64 runners, merge manifest, tag with git SHA → push to ECR → deploy via SSM Run Command: backup → pull → migrate → start → readiness check → **automatic rollback** to the previous SHA if readiness fails.
- `infra/scripts/rollback.sh <sha>`; keep the last 5 images.

**Portability (MUST)**
- The core system runs with only Docker + PostgreSQL + local or any S3-compatible storage (v2.1: Redis no longer required).
- Every cloud service sits behind a port (Storage, LLMClient, JobQueue); provider choice by environment variables.
- Documented migration targets: Oracle Cloud Always Free (Arm; currently 2 OCPU / 12 GB after the 2026 reduction) or split hosting (Vercel + managed Postgres free tier + container host). Multi-arch images make the move a config change, not a rebuild.

**Cost guardrails**
- AWS account is on the Free Plan (created ~2026-09-07; up to US$200 credits; plan ends ~early March 2027 or when credits run out; **the account is closed if not upgraded before the plan ends**). Decision D3 due by February 2027: upgrade to Paid (credits remain usable until their expiry) or migrate.
- Expected burn: `t4g.small` + 20 GB gp3 + **public IPv4 (charged hourly)** ≈ US$20–25/month in Singapore → verify with AWS Pricing Calculator at CP-00 and set Budget alarms at 50/80/100 % of monthly plan.
- Complete the five AWS credit activities (Budget, EC2, RDS, Lambda, Bedrock) early; delete test resources afterwards.
- App-level caps: per-document cost cap, daily LLM spend cap, kill switch `PAID_MODELS_ENABLED=false`.
- MUST NOT provision: NAT Gateway, ALB, EKS, always-on GPU instances, SageMaker endpoints.
- The fine-tuned 2B VLM is **not** served on the CPU server. Production uses API VLM + CPU amount reader + CPU OCR; the fine-tuned model is published on Hugging Face with its benchmark results.

---

## 16. Frontend (`apps/web`)

**Pages**
- `/login`
- `/upload` — drag-and-drop, multiple files, per-file progress and status
- `/queue` — `NEEDS_REVIEW` list; filter by doc type/vendor; sort by lowest confidence
- `/documents/[id]` — image/PDF viewer (left) with bbox overlays (colored by `bbox_source`); fields (right) with confidence badges and evidence (which signals disagreed); inline correction with reason; approve/reject; keyboard shortcuts
- `/purchase-orders` — list, detail, match status and discrepancies
- `/dashboard` — automation rate, abstain rate, cost per doc, latency, correction hotspots by field/vendor
- `/about` — method, limitations, links to eval report, dataset, models

**Standards**
- Next.js 16 conventions: `proxy.ts` (not `middleware.ts`) for auth redirects; `await` all dynamic APIs (`cookies()`, `headers()`, `params`); ESLint via CLI (no `next lint`).
- TypeScript strict; API access only via the generated client; Zod for form validation.
- Every view has loading, empty, and error states.
- Accessibility: labels, focus order, keyboard use, sufficient contrast.
- No secrets in client code; auth via httpOnly cookies; never store tokens in localStorage.
- Playwright e2e for the critical path.
- UI copy in Indonesian (persona); code and docs in English.
- Contract-first: web work may start against a mock server generated from the OpenAPI draft (e.g., Prism) before the API is complete.

---

## 17. Documentation set ("documented" means all of these exist and are current)

| File | Content |
|---|---|
| `README.md` | First screen in plain language: what, why, headline metric + risk–coverage chart, 90-second demo video, live link, architecture image, quickstart, limitations |
| `docs/BLUEPRINT.md` | This file |
| `docs/CHECKPOINTS.md` | CP-00..CP-33: goals, owners, gates, debug playbooks (v2.1) |
| `docs/FUNCTION_SPECS.md` | Contracts for every significant function (FS-IDs), examples, edge cases, tests (v2.1) |
| `docs/PROGRESS.md` + `docs/progress/CP-NN.md` | Status board + per-checkpoint evidence logs (v2.1) |
| `docs/TECH_REFRESH_2026-10.md` | Tool/model pins with verification dates and sources (v2.1) |
| `docs/ARCHITECTURE.md` | C4 context + container diagrams, pipeline, state machine, data model |
| `docs/adr/NNNN-title.md` | MADR template: context, options, decision, consequences |
| `docs/RUNBOOK.md` | Deploy, rollback, backup, restore (+ drill log), rotate secrets, incident checklist |
| `docs/EVAL_REPORT.md` | Latest full evaluation with versions and CIs |
| `docs/DATASET_CARD.md` | Sources, licenses, tiers, splits, limitations, fictional-data statement |
| `docs/MODEL_CARD.md` | Per model: base, data, training cost, metrics, limitations, intended use |
| `docs/SECURITY.md` | Reporting process, threat model summary |
| `docs/FAILURE_LOG.md` | Date, symptom, root cause, fix, test added, checkpoint where introduced |
| `docs/HOW_I_USED_AI.md` | Honest account: AI implemented the code; what Arka decided, studied, tested, changed |
| `CONTRIBUTING.md`, `CHANGELOG.md` | Workflow, commit conventions, release notes |

Code comments explain *why*, not *what*. Public functions have Google-style docstrings referencing their FS-ID.

---

## 18. Milestones (pause-safe: each one ends with a publishable artifact) — mapped to checkpoints

Calendar (v2.1, ADR-0013): **12 weeks, Mon 2026-10-05 → Fri 2026-12-25**, capacity ~35–40 h/week.

```yaml
milestones:
  - id: M0
    name: Foundation
    weeks: [1]                 # 2026-10-05 .. 10-09
    checkpoints: [CP-00, CP-01, CP-02, CP-03, CP-04]
    deliverables:
      - Repo with monorepo skeleton, pre-commit, CI (lint, typecheck, tests, import-linter, gitleaks, zizmor)
      - docs/BLUEPRINT.md, AGENTS.md, README (problem + persona + metrics), ADR-0001 domain choice, ADR-0002 provider-agnostic adapters
      - Pydantic schemas (§3.2), domain FSM, ports
      - Money/dates/NPWP/terbilang/arithmetic validators (learning-critical: AI implements, Arka studies + tests)
      - AWS Budget configured; domain registered
    done_when:
      - CI green on main; gates cp00..cp04 green; core coverage >= 90%
  - id: A
    name: Data + baselines
    weeks: [2, 3, 4]           # 10-12 .. 10-30
    checkpoints: [CP-05, CP-06, CP-07, CP-08, CP-09, CP-10, CP-11, CP-12, CP-13]
    deliverables:
      - Data sources with manifests + leakage check
      - Scenario generator + renderers (digital, handwriting_like, composite, photo_sim)
      - T3: 100 handwritten docs (30 calib / 70 test)
      - Dataset v0.1 with tiers T0–T3 and calib split; dataset card; publishable parts on Hugging Face
      - Eval harness v1 (§11) incl. replay, CIs, risk–coverage and reliability plots
      - Baselines B1a, B1b, B2, B3, B4 evaluated; docs/EVAL_REPORT.md v0.1
      - Optional: Kaggle Community Benchmark; LinkedIn post 1 (benchmark findings)
    done_when:
      - Every baseline has per-tier metrics with CIs, cost, latency, peak RSS; report reproducible from one command
  - id: B
    name: Models + calibration
    weeks: [5, 6, 7]           # 11-02 .. 11-20 (≈3.5 days slack inside)
    checkpoints: [CP-14, CP-15, CP-16, CP-17, CP-18, CP-19, CP-20]
    deliverables:
      - Amount reader experiment (CRNN from scratch vs TrOCR fine-tune) with report; ONNX export
      - Grounding by OCR alignment
      - VLM LoRA fine-tune with adoption decision (§5.3)
      - Calibrator + SGR abstention policy + ablation study
      - MLflow runs; model cards; adapters/models on Hugging Face; EVAL_REPORT v0.2
    done_when:
      - Risk–coverage curve (empirical + certified) and ablation reproducible; adoption decisions recorded as ADRs
  - id: C
    name: Product
    weeks: [8, 9, 10, 11]      # 11-23 .. 12-18
    checkpoints: [CP-21, CP-22, CP-23, CP-24, CP-25, CP-26, CP-27, CP-28, CP-29, CP-30, CP-31, CP-32]
    deliverables:
      - DB + migrations, adapters, worker pipeline (Procrastinate + LangGraph), validators, PO matching, FSM
      - API with sessions/RBAC/CSRF; review UI with grounding; dashboard
      - Observability (§12), security baseline (§13), backups + first restore drill (§14)
      - Deploy with automatic rollback (§15)
      - Vendor memory (SHOULD; else backlog)
    done_when:
      - Live demo; Playwright critical path green; restore drill logged; security checklist §13 complete
  - id: L
    name: Launch + buffer
    weeks: [12]                # 12-21 .. 12-25
    checkpoints: [CP-33]
    deliverables:
      - README final, 90-second video, LinkedIn post 2, release v1.0.0
backlog_after_C: [n8n email intake, MCP server (read-only tools), read-only text-to-SQL analytics, RAG over contract clauses]
cut_line_if_behind: [CP-32 vendor memory, TrOCR arm of CP-15, Sentry, multi-arch (arm64 only), dashboard extras]
never_cut: [tests, eval honesty (CIs), security baseline, backups + restore drill]
```

Rule: if the bootcamp final project interrupts, stop at the end of the current **checkpoint** (not milestone): every checkpoint ends green and tagged, so pausing is always safe. Work items inside a checkpoint are issues of ≤ 1 day, each with acceptance criteria.

---

## 19. Role briefs for AI agents

Each agent reads §0–§3, its own brief, §20, the **current checkpoint** in `docs/CHECKPOINTS.md`, the FUNCTION_SPECS entries listed there, and the sections listed under "references".

### R1 — Architect / Tech Lead
- **Mission:** keep the system coherent with this blueprint.
- **Owns:** this file, ADRs, issue breakdown per checkpoint, PR review for layering and standards, `docs/PROGRESS.md` hygiene.
- **Must:** break checkpoints into ≤ 1-day issues with acceptance criteria; reject PRs that violate §7.1 or §9; keep the open-decisions list (§22) current.
- **Must not:** change metrics or scope without Arka's approval and an ADR.
- **References:** §6, §7, §9, §18, §21, §22; CHECKPOINTS §0.

### R2 — Data & ML Engineer
- **Mission:** data generation, training, and experiment tracking.
- **Owns:** `packages/ml/datagen`, `train/trocr`, `train/vlm_lora`, `calibrate/` plumbing, eval runner/replay plumbing, manifests, Kaggle notebooks, MLflow, model cards, dataset card.
- **Must:** respect licenses (§4.1) and leakage rules (§4.4); make every run reproducible (§5.8); report negative results.
- **Must:** write a study guide (`docs/learning/CP-NN.md`) for every learning-critical module you implement (§20).
- **Must not:** use AI-generated handwriting in any test tier.
- **References:** §4, §5, §11.

### R3 — Backend Engineer
- **Mission:** API, worker, adapters, database.
- **Owns:** `apps/api`, `apps/worker`, `packages/adapters`, `migrations/`, `core/models` and `core/ports`.
- **Must:** follow §6 contracts and §9 standards; idempotent jobs; transactional enqueue; reversible migrations; contract tests per adapter.
- **Must not:** import `ml` at runtime; put I/O into `core`; use LangGraph interrupts for review.
- **References:** §3.2, §6, §7, §9, §10, §13.

### R4 — Frontend Engineer
- **Mission:** the review experience.
- **Owns:** `apps/web`.
- **Must:** use the generated API client; implement §16 pages and states; Playwright critical path; follow Next.js 16 conventions.
- **Must not:** call model providers from the browser; store tokens in localStorage.
- **References:** §6.3, §16, §13.

### R5 — DevOps / SRE
- **Mission:** reliable, cheap, portable operations.
- **Owns:** `infra/`, CI/CD workflows, OIDC/IAM, SSM, backups and restore scripts, monitoring and alerts, cost guardrails, memory budget.
- **Must:** automatic rollback; pre-deploy backup; monthly restore drill; multi-arch images; Budget alarms; SHA-pinned actions.
- **Must not:** provision anything listed as forbidden in §15.
- **References:** §12, §13, §14, §15.

### R6 — QA / Evaluation
- **Mission:** catch regressions before users and recruiters do.
- **Owns:** test plans, **acceptance tests from FUNCTION_SPECS (written before the implementation)**, property tests, golden tests, checkpoint gate scripts, eval gate wiring, flaky-test triage.
- **Must:** write the failing test first for every reported bug (§10); keep `evals/baseline.json` honest.
- **References:** §2, §10, §11; CHECKPOINTS §0; FUNCTION_SPECS.

### R7 — Security Reviewer
- **Mission:** keep the baseline in §13 true.
- **Owns:** threat model per milestone, review of auth/upload/LLM-input code, CI supply-chain config review, triage of scanner findings.
- **References:** §13, §14.

### R8 — Documentation
- **Mission:** make the project understandable in 10 seconds (recruiter) and 10 minutes (engineer).
- **Owns:** §17 document set, CHANGELOG, diagrams; drafts `HOW_I_USED_AI.md` from PR labels for Arka to edit.
- **Must not:** claim results that are not in `EVAL_REPORT.md`.
- **References:** §1, §2, §17.

---

## 20. Ownership and AI-assist policy (MUST) — v2.2.0, ADR-0014

**Workflow per checkpoint:** brainstorm together → **AI implements** (code, tests, docs, gate green) → **Arka
studies** (`docs/learning/CP-NN.md`) → **Arka tests** (gate, manual exercises, own tests, break-it attempts) →
fixes by AI → **Arka signs off** (progress log section "What I tested / learned") → merge + tag `cp-NN`.

**Why:** Arka must be able to explain, debug and defend the core logic in interviews. The code is AI-written; the
understanding and the verification must be Arka's.

**LEARNING-CRITICAL modules** (formerly "human-owned"): `packages/core/validation/*`, `packages/core/matching/*`,
`packages/core/confidence/*`, `packages/ml/src/cocok_ml/calibrate/*`, `packages/ml/eval/metrics/*`,
`packages/ml/train/crnn/`. For these the AI MUST also deliver a study guide with: walkthrough of the code, the
concepts and the "why" of each design choice, manual test exercises, break-it exercises (mutations the tests must
catch), and explain-back questions. Sign-off additionally requires Arka's own answers to the explain-back questions
and at least 3 test cases written by Arka (or a bug he found).

**Honesty:** `docs/HOW_I_USED_AI.md`, the README and interviews state plainly that the AI implemented the code and
Arka brainstormed the design, verified, tested and can explain it. AI-written code is never presented as
hand-written.

**Every PR:** Arka reviews and must be able to explain it; PRs carry the `ai-assisted` label.

---

## 21. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Indonesian-word handwriting variety limited to Arka's styles | High | Medium | Disclose; multi-writer tiers T1/T2 cover critical fields; optional helper writers |
| Fine-tuned VLM does not beat zero-shot | Medium | Low | Valid finding; keep API route; document in ADR |
| Kaggle Benchmarks terms disallow our use | Low | Low | Fall back to remaining OpenAI credits, Bedrock (AWS credits), Gemini free tier (synthetic only) |
| Scope creep | High | High | Checkpoint gates; backlog list; cut line; R1 enforces |
| License violation (ORAND ND, CVL NC, AGPL deps) | Medium | High | License field in manifests; publish script blocks non-publishable sources; `pip-licenses` CI check |
| Data leakage between splits | Medium | High | sha256 + source-id overlap check in CI |
| AWS Free Plan ends (~Mar 2027) or credits run out early | Certain | Medium | Portability (§15); Budget alarms; decision D3 by Feb 2027 |
| LLM cost overrun | Low | Medium | Per-doc and daily caps; kill switch; Budget alarms; replay-mode eval gate |
| Bootcamp final project interrupts | Medium | Medium | Pause-safe checkpoints (every CP ends green + tagged) |
| Prompt injection via document text | Medium | Medium | §13 LLM rules; schema validation; no tools from document content |
| **(v2.1)** Certified 1 % not reachable with available calib data | Medium | Medium | Report honestly (certified coverage = 0 is a valid result); enlarge calib via generator; T2-calib ≥ 300 |
| **(v2.1)** transformers v5 / Qwen3.5 upstream bugs; fp16 instability on T4 | Medium | Medium | Exact pins; 50-step smoke run; Modal L4 fallback |
| **(v2.1)** OOM on 2 GB host | Medium | High | Memory budget + container limits (§15); no torch in worker image; swap |
| **(v2.1)** CI supply-chain compromise | Low | High | ADR-0011 controls |
| **(v2.1)** Calendar slip | Medium | Medium | 12-week calendar with buffer; cut line (§18) |

---

## 22. Open decisions (owner: Arka)

| ID | Decision | Default until decided |
|---|---|---|
| D1 | Exact persona | Building-materials store receiving goods from small suppliers |
| D2 | UI language | Indonesian UI, English docs |
| D3 | AWS after Free Plan: upgrade to Paid vs migrate | Decide by Feb 2027; migrate if no card risk is acceptable |
| D4 | Publish benchmark on Kaggle Community Benchmarks | Yes, if terms allow (image input is supported) |
| D5 | License for published dataset | CC BY 4.0 for own/synthetic parts; CC BY-NC for parts derived from CVL; ORAND never published |
| D6 | Accept ADR-0003..0013 (v2.1 changes) | Proposed; build proceeds on v2.1 defaults unless Arka rejects an ADR before its first checkpoint |
| D7 | Domain name for same-site topology (ADR-0008) | Buy before CP-25; until then local dev only |
| D8 | AWS region | Singapore (ap-southeast-1) unless Jakarta (ap-southeast-3) offers `t4g.small` at ≤ price — check at CP-00 |
| D9 | Repo visibility during Milestone A | Public from CP-01 (free arm64 runners); data stays private on HF until license review |

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
| NPWP | Taxpayer ID; 16 digits (legacy 15-digit IDs are prefixed with 0; personal NPWP equals NIK) |
| NIK | National ID number (16 digits) |
| NITKU | Business-activity-place ID (22 digits = NPWP + 6-digit place code; `000000` = head office) |
| PPN | Value-added tax (VAT) |
| DPP | Tax base; *DPP nilai lain* = 11/12 × price for non-luxury goods under PMK 131/2024 |
| PKP | Pengusaha Kena Pajak — VAT-registered business (only PKP issue faktur pajak) |
| Coretax | Indonesian tax administration system |
| UMKM | Micro, small and medium enterprises |
| Rp format | `Rp 1.250.000,-` → dot = thousands separator, comma = decimal separator |
| three-way match | PO ↔ surat jalan (delivered qty) ↔ invoice (billed qty and price) |

---

## 24. References (verify availability and license at time of use; accessed 2026-10-01)

- CVL digit strings: https://cvl.tuwien.ac.at/research/cvl-databases/icdar2013-handwritten-digit-and-digit-string-recognition-competition/
- ORAND-CAR-2014 + CVL HDS (ICFHR 2014): https://www.orand.cl/icfhr2014-hdsr/
- Handwritten names (CC0): https://www.kaggle.com/datasets/landlord/handwriting-recognition
- CORD v2: https://huggingface.co/datasets/naver-clova-ix/cord-v2
- Base VLM: https://huggingface.co/Qwen/Qwen3.5-2B · Unsloth guide: https://unsloth.ai/docs/models/qwen3.5/fine-tune
- OCR VLMs: https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6 · GLM-OCR (Zhipu, MIT)
- Pretrained handwriting OCR: https://huggingface.co/microsoft/trocr-small-handwritten
- CPU OCR for grounding: https://pypi.org/project/rapidocr/
- Kaggle Community Benchmarks: https://www.kaggle.com/docs/benchmarks · SDK: https://github.com/Kaggle/kaggle-benchmarks
- Queue: https://pypi.org/project/procrastinate/ · arq status: https://github.com/python-arq/arq
- LangGraph backward compatibility: https://docs.langchain.com/oss/javascript/langgraph/backward-compatibility
- SGR: Geifman & El-Yaniv 2017, https://arxiv.org/abs/1705.08500
- PPN: PMK 131/2024 — https://www.pajak.go.id/en/node/113453
- NITKU format: https://www.online-pajak.com/bisnis/nitku-adalah/
- AWS Free Tier terms: https://aws.amazon.com/free/terms
- Trivy action compromise advisory: https://github.com/aquasecurity/trivy/security/advisories/GHSA-69fq-xp46-6x23
