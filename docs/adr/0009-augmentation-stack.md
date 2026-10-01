---
status: proposed
date: 2026-10-01
decision-makers: Arka
consulted: R2
blueprint-sections: "§4.2 (photo_sim), §8 (ml)"
---

# ADR-0009: Build `photo_sim` on torchvision v2 + small OpenCV ops; do not depend on Albumentations

## Context and Problem Statement

v2.0.0 names Albumentations for `photo_sim` (perspective, blur, shadow, low light, JPEG, paper texture, crumple).
As of 2026-10-01:

* The MIT-licensed `albumentations` package is **archived**; last release 2.0.8 on 2025-05-27, no maintenance.
* The maintained successor **AlbumentationsX** is **AGPL-3.0-only or commercial**. The dataset and code are meant
  to be public and reused; an AGPL dependency in the data pipeline creates licensing questions we do not need.
* Augraphy (document-specific, MIT) has not released since 2023-12.

## Decision Drivers

* License clarity for a public repo and a CC-BY dataset.
* Every augmentation must be **seeded and logged** (params recorded in the manifest) for reproducibility.
* Each op is small enough for Arka to read and explain.

## Considered Options

1. AlbumentationsX (AGPL).
2. Pin archived `albumentations==2.0.8` (MIT).
3. **`torchvision.transforms.v2` (BSD-3: perspective, affine, blur, color jitter, JPEG) + ~5 custom NumPy/OpenCV
   ops (shadow gradient, paper texture blend, crumple via smooth displacement field, low-light gamma + noise,
   ink bleed) in `cocok_ml.datagen.photo_sim`.**

## Decision Outcome

Chosen option: **3**; option 2 is the allowed fallback if a needed op is missing (pin exact version, isolate
behind `photo_sim` so it can be removed later).

Each op is a pure function `op(image: np.ndarray, rng: np.random.Generator, **params) -> (image, params_used)`,
and box coordinates are transformed with the same geometric matrix so ground-truth bboxes stay valid.

### Consequences

* Good: permissive licenses only; full control of bbox transforms; reproducible.
* Bad: ~200 lines of custom code to own and test. Mitigation: golden-image tests with fixed seeds (CP-08).

### Confirmation

* CP-08 gate: for 50 seeded samples, transformed GT bboxes still contain the rendered field text (pixel check
  against a mask render), and `photo_sim` is deterministic (same seed → identical bytes hash).
* `pip-licenses` report in CI flags any AGPL/GPL dependency in the `ml` extra (CP-05 onward).

## More Information

* https://albumentations.ai/docs/license/
* https://pypi.org/project/augraphy/ (last release 8.2.6, 2023-12-31)
* torchvision `transforms.v2` docs (JPEG transform available since 0.19)
