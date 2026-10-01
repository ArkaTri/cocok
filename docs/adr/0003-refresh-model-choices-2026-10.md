---
status: proposed
date: 2026-10-01
decision-makers: Arka
consulted: R1, R2
blueprint-sections: "§5.2, §5.3, §8, §24"
---

# ADR-0003: Refresh model choices to the October 2026 state of the art

## Context and Problem Statement

Blueprint v2.0.0 names `Qwen/Qwen3-VL-2B-Instruct` as the fine-tuning base, "PaddleOCR-VL or GLM-OCR"
for baseline B1, and "LoRA / QLoRA" as the method. Since then:

* **Qwen3.5 small series** (0.8B / 2B / 4B / 9B, released Feb–Mar 2026, Apache-2.0) is *natively multimodal*:
  one checkpoint handles text and images. `Qwen/Qwen3.5-2B` reports OCRBench ≈ 84–85 and CC-OCR ≈ 73–76.
  Newer Qwen generations (3.6, 3.8) ship only ≥ 27B open weights, so Qwen3.5-2B is the current small option.
* Unsloth's Qwen3.5 guide states: **"It is not recommended to do QLoRA (4-bit) training on the Qwen3.5 models"**,
  and **transformers v5 is required** ("Older versions will not work"). bf16 LoRA on 2B needs ≈ 5 GB VRAM.
* OCR-specialist VLMs moved: **PaddleOCR-VL-1.6** (≈1B, Apache-2.0, released 2026-05-28, OmniDocBench v1.6 ≈ 96.3)
  and **GLM-OCR** (0.9B, MIT, Mar 2026, supports key-information extraction) lead open document parsing.
* Kaggle T4 GPUs (Turing, sm_75) have **no bf16 support**; training must run in fp16 there.

## Decision Drivers

* Use what a 2026 document-AI team would actually benchmark against.
* Fit the free compute we have (Kaggle T4 16 GB; Modal credits as fallback).
* Keep the "does fine-tuning beat zero-shot?" experiment honest (same base for B3 and fine-tune).

## Considered Options

1. Keep Qwen3-VL-2B-Instruct + QLoRA (v2.0.0 as written).
2. **Qwen3.5-2B (native multimodal) + 16-bit LoRA via Unsloth/TRL; vision tower frozen in v1.**
3. Qwen3.5-4B + LoRA (≈10 GB bf16; tighter on T4, slower).

## Decision Outcome

Chosen option: **2**. Same parameter class as v2.0.0 (so all budgets still hold), one generation newer,
Apache-2.0, and the tooling vendor explicitly supports it. QLoRA is dropped because the toolchain authors
advise against it for this architecture; 2B fits in 16-bit LoRA anyway.

Baselines become:

| ID | v2.0.0 | v2.1.0 |
|---|---|---|
| B1 | PaddleOCR-VL or GLM-OCR → text LLM | **B1a** PaddleOCR-VL-1.6 → text LLM; **B1b** GLM-OCR KIE prompt → JSON (no second LLM) |
| B2 | Zero-shot API VLMs | unchanged; record exact model id + date; Kaggle Benchmarks **does** support image input (`kaggle-benchmarks` SDK `images.from_path`) |
| B3 | Qwen3-VL-2B zero-shot | **Qwen3.5-2B zero-shot** (non-thinking mode) |
| B4 | Docling | Docling (latest 2.x) **and** `pypdfium2` text layer → LLM (see ADR-0010) |

### Consequences

* Good: current models; no 4-bit quantization noise; faster experiments.
* Bad: transformers v5 is required → pin it in the `ml` extra and in the Kaggle notebook; Qwen3.5 uses custom
  Triton kernels that **compile slowly on T4** → first step is slow, cache kernels between sessions.
* Bad: fp16 on T4 can overflow → mandatory 50-step smoke run with loss/NaN check before any long run (CP-17).
  Fallback: Modal credits on an L4/A10G (bf16-capable).
* Thinking mode stays **off** (model card warns 2B "is more prone to entering thinking loops").

### Confirmation

* CP-13 gate: B3 runs with `Qwen/Qwen3.5-2B` at a pinned HF revision hash, logged in MLflow.
* CP-17 gate: smoke run passes (finite loss, decreasing over 50 steps) before full training is allowed.

## Pros and Cons of the Options

### 1. Qwen3-VL-2B + QLoRA
* Good, because no change.
* Bad, because one generation old; QLoRA saves memory we do not need on 2B and adds quantization error.

### 3. Qwen3.5-4B
* Good, because likely higher accuracy.
* Bad, because ≈2× VRAM and time on T4; harder to iterate inside 30 GPU-h/week; serve cost higher.
  Keep as a stretch run only if 2B is close to winning.

## More Information

Sources (accessed 2026-10-01):
* https://huggingface.co/Qwen/Qwen3.5-2B
* https://unsloth.ai/docs/models/qwen3.5/fine-tune
* https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6
* https://blog.roboflow.com/best-open-source-ocr-models/ (2026-08-03 ranking)
* https://github.com/Kaggle/kaggle-benchmarks/blob/ci/cookbook.md (image inputs)

Revisit: at CP-12 (before baselines run) — check for a newer small open VLM; swap only if it is ≥ same license
freedom and fits T4.
