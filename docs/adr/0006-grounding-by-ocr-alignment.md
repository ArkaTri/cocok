---
status: proposed
date: 2026-10-01
decision-makers: Arka
consulted: R2, R3
blueprint-sections: "§3.2 (bbox), §5.1, §5.6, §16"
---

# ADR-0006: Ground extracted values by aligning them to OCR line boxes, not by trusting VLM coordinates

## Context and Problem Statement

Two things in v2.0.0 depend on a **bounding box** for each field:

1. The amount reader reads "the `total_amount` crop (bbox from primary extractor)" (§5.1 step 4).
2. The review UI shows "field ↔ location on the image" (§16).

Coordinates emitted by general-purpose VLMs are model-specific and often unreliable (some APIs document a
detection mode, e.g. Gemini's normalized `box_2d`; many do not). If the bbox is wrong, the "independent second
read" reads the wrong pixels and fails **in the same direction** as the primary extractor — the ablation would
then under-credit the amount reader for reasons unrelated to its quality.

## Decision Drivers

* The second read must be *independent* of the primary extractor's failure modes.
* Must run on CPU on the 2 GB host.
* Must work identically for every primary route (API VLM, local VLM, OCR pipeline).

## Considered Options

1. Trust each extractor's bbox (v2.0.0).
2. **Run a light CPU OCR detector+recognizer (RapidOCR, PP-OCR ONNX models, Apache-2.0) on every visual
   document; align each extracted value string to OCR lines (normalized fuzzy match); use the aligned line box.
   Fall back to the extractor's bbox, then to "no grounding" (forces review of that field).**
3. Ask the VLM for a bbox and verify with OCR only when present.

## Decision Outcome

Chosen option: **2**. Grounding becomes a deterministic, testable function (`ground_value`, see
FUNCTION_SPECS FS-AD-07), and it yields an extra confidence signal for free: `s_ocr_agree` (similarity
between the extracted value and the best OCR line).

For `total_amount` on handwritten documents the OCR *text* may be wrong, but the **box** of the line matching
the "Rp …" / "Jumlah" region is usually right — alignment uses both text similarity and layout anchors
(keywords: `Jumlah`, `Total`, `Rp`, `Terbilang`).

### Consequences

* Good: amount-reader independence is real; ablation is meaningful; UI grounding works for every route.
* Good: digital PDFs get exact boxes from the text layer (pypdfium2 char boxes) — same alignment function.
* Bad: +100–300 ms CPU per page and ~100–200 MB RSS. Measured at CP-16; budget enforced at CP-30.
* Bad: alignment can fail on messy handwriting → field gets `bbox=null`, `s_ocr_agree=0`, routed to review.
  This is the correct behavior for an abstaining system.

### Confirmation

* CP-16 gate: on T0+T2-test, `total_amount` grounding IoU ≥ 0.5 vs renderer ground-truth bbox is reported
  (no target — honest number), and alignment latency p95 on CPU is logged.
* CP-20 ablation includes "amount reader with GT bbox" vs "with aligned bbox" to quantify grounding loss.

## More Information

* https://pypi.org/project/rapidocr/ (3.9.x, Apache-2.0, onnxruntime engine)
* https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/bounding-box-detection
