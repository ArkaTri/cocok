# Tech refresh — verified 2026-10-01

Every tool/model/service named in the blueprint, checked against its current release on 2026-10-01.
**Rule:** pin exact versions in lockfiles at CP-01/CP-12/CP-17; this table records *what state of the world the
decisions were based on*. Re-verify any row older than 90 days before relying on it.

## Models

| Item | Blueprint v2.0.0 | State on 2026-10-01 | Decision (v2.1) | Source |
|---|---|---|---|---|
| Small open VLM (base for LoRA, B3) | Qwen3-VL-2B-Instruct | **Qwen3.5-2B** (Feb–Mar 2026, Apache-2.0, natively multimodal; OCRBench ≈ 84–85). Qwen 3.6/3.8 open weights are ≥ 27B only | Switch to Qwen3.5-2B | huggingface.co/Qwen/Qwen3.5-2B; codersera Qwen guide |
| LoRA method | LoRA / QLoRA | Unsloth: "not recommended to do QLoRA (4-bit) training on the Qwen3.5 models"; transformers **v5 required**; 2B bf16 LoRA ≈ 5 GB | 16-bit LoRA; fp16 on T4 | unsloth.ai/docs/models/qwen3.5/fine-tune |
| OCR-VLM baseline | PaddleOCR-VL or GLM-OCR | **PaddleOCR-VL-1.6** (2026-05-28, ≈1B, Apache-2.0, OmniDocBench v1.6 ≈ 96.3); **GLM-OCR** (Mar 2026, 0.9B, MIT, KIE) | Both, as B1a/B1b | HF PaddleOCR-VL-1.6; Roboflow ranking 2026-08-03 |
| Digital PDF parsing | Docling | Docling **2.131.0** (2026-09-29); granite-docling-258M VLM option | Keep as B4; prod uses pypdfium2 first (ADR-0010) | pypi.org/project/docling |
| Handwriting OCR (pretrained arm) | trocr-small-handwritten | Still the canonical HF handwriting baseline | Keep | HF model card |
| CPU OCR for grounding | — | **RapidOCR 3.9.x** (2026-07, Apache-2.0, ONNX Runtime) | Add (ADR-0006) | pypi.org/project/rapidocr |
| Embeddings (if needed) | voyage-4 family | Voyage 4 family released 2026-01-15; free token allowance | Keep, only if needed | blog.voyageai.com/2026/01/15/voyage-4 |
| API VLMs (B2) | OpenAI / Bedrock / Gemini / Kaggle | Model line-ups change monthly; Gemini free tier content **is** used to improve products | Record exact model id + date per run; free tiers = synthetic only | Gemini pricing/data-use pages |

## Platforms and services

| Item | State on 2026-10-01 | Consequence | Source |
|---|---|---|---|
| Kaggle Community Benchmarks | `kaggle-benchmarks` SDK supports image inputs (`images.from_path/from_url/from_base64`) | D4 viable if terms allow | github.com/Kaggle/kaggle-benchmarks (cookbook) |
| Kaggle GPU | T4 (Turing) has no bf16; weekly quota shown in account settings | fp16 training; verify quota at CP-00 | Kaggle docs |
| Modal | Monthly free credits (~US$30) | Fallback GPU (L4/A10G, bf16) | Modal pricing |
| AWS Free Plan | ≤ US$200 credits (100 + 100 via activities), up to 6 months; account **closed** if not upgraded before end | D3 by Feb 2027; Budget alarms | AWS Free Tier docs; costbench summary |
| Oracle Always Free | Ampere A1 reduced to 2 OCPU / 12 GB in 2026 | Blueprint already correct | InfoQ 2026-07 |
| GitHub arm64 runners | Free for public repos (GA 2025-08) | Native multi-arch builds | GitHub changelog 2025-08-07 |
| Trivy GitHub Action | Tag-poisoning compromise (Mar 2026, 75/76 tags) | SHA pinning + least privilege (ADR-0011) | GHSA-69fq-xp46-6x23 |
| Indonesian PPN | PMK 131/2024 (from 2025-01-01): 12 % rate; non-luxury DPP = 11/12 × price (effective 11 %); no change announced for 2026 | Encode in `rules/tax.yaml`; re-verify when writing | pajak.go.id; DDTCNews |
| NPWP / NITKU | NPWP 16 digits (legacy 15 → prefix 0; personal = NIK); NITKU = NPWP16 + 6-digit place code (000000 = HQ) | FS-CV-04/05 | online-pajak.com (NITKU) |

## Libraries and frameworks

| Item | Version/state on 2026-10-01 | Decision | Source |
|---|---|---|---|
| arq | **Maintenance-only mode** | Replace with Procrastinate (ADR-0004) | github.com/python-arq/arq README |
| Procrastinate | 3.10.0 (2026-09-23), production/stable, asyncio, PG ≥ 13 | Adopt | pypi.org/project/procrastinate |
| LangGraph | 1.2.12 (2026-09-21), production/stable | Keep; no long-lived interrupts (ADR-0005) | pypi.org/project/langgraph |
| PostgreSQL | 18 with native `uuidv7()` | Adopt PG18 | postgresql.org release notes 18 |
| Langfuse Python SDK | **v4** (OTel-native, Mar 2026); 4.16.0 on 2026-09-30; v2 `trace()/span()` deprecated | Use v4 APIs (`get_client`, `@observe`) | pypi.org/project/langfuse |
| MLflow | 3.16.1 (2026-09-16) | Use 3.x | pypi.org/project/mlflow |
| ty (Astral type checker) | 0.0.81 beta (2026-09-15) | **Keep mypy**; revisit at ty 1.0 | github.com/astral-sh/ty/releases |
| Next.js | 16.x (16.3 current); `proxy.ts`, Turbopack default, `next lint` removed, async dynamic APIs | Use Next 16 conventions | nextjs.org/blog; makerkit Next 16 guide |
| FastAPI auth libs | Official tutorial uses `pwdlib[argon2]` + PyJWT; passlib unmaintained | pwdlib; no JWT (ADR-0008) | fastapi.tiangolo.com security tutorial |
| Albumentations | MIT package archived (2.0.8, 2025-05-27); successor AlbumentationsX is AGPL/commercial | torchvision v2 + own ops (ADR-0009) | albumentations.ai/docs/license |
| Augraphy | Last release 2023-12-31 | Not used | pypi.org/project/augraphy |
| Material for MkDocs | Maintenance mode; EOL 2026-11-05; successor **Zensical** (built-in mkdocstrings replacement) | Optional docs site on Zensical | squidfunk blog; Zensical releases |
| OpenTelemetry GenAI semconv | Still experimental in 2026 | Use, pin semconv version | OTel GenAI status write-ups 2026 |
| Redis | Redis 8 under AGPLv3 (or Valkey BSD fork) | Not needed after ADR-0004 | redis.io licenses |
