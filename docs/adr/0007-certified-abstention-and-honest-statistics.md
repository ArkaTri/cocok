---
status: proposed
date: 2026-10-01
decision-makers: Arka
consulted: R2, R6
blueprint-sections: "§2, §4.3, §4.4, §5.6, §11"
---

# ADR-0007: Choose τ with a finite-sample risk guarantee; report every metric with a confidence interval

## Context and Problem Statement

The headline metric is "automation rate while field-level error among auto-processed docs ≤ 1 %".
v2.0.0 picks τ empirically on the calib split. Three statistical problems:

1. **Empirical ≤ 1 % is not ≤ 1 %.** If τ is pushed down until the calib error sits right at 1 %, the true error
   on new data exceeds 1 % roughly as often as not (selection on noise / winner's curse). We need an upper
   confidence bound (UCB), not a point estimate.
2. **Sample size.** With a one-sided 95 % Clopper–Pearson bound, certifying risk ≤ 1 % needs at least:

   | errors among auto-approved docs | minimum auto-approved docs |
   |---|---|
   | 0 | 299 |
   | 1 | 473 |
   | 2 | 628 |
   | 3 | 773 |

   (computed with `scipy.stats.beta.ppf`, δ = 0.05, one fixed threshold). SGR's search additionally splits δ over
   ⌈log₂ n⌉ steps (Bonferroni), which raises the zero-error requirement to ≈ 528–540 accepted documents for a
   calib set of 500–2 000 documents. A calib split that auto-approves fewer docs **cannot** certify 1 % — the
   honest outcome is "coverage 0 at certified 1 %", not a pretty number.
3. **Tiny tiers.** T3 with 30–50 docs has a 95 % CI width of ≈ ±10 pp on a 90 % accuracy. Per-tier numbers
   without intervals invite over-reading.

Also: field errors inside one document are correlated, so field-level binomial bounds overstate the
effective sample size.

## Decision Drivers

* The headline claim must survive a sceptical reviewer.
* No change to the *definition* of the headline metric (§2 is frozen) — only to how τ is chosen and how
  results are reported.

## Considered Options

1. Empirical τ on calib (v2.0.0).
2. **Selection with Guaranteed Risk (SGR; Geifman & El-Yaniv 2017): binary-search τ, accept the lowest τ whose
   document-level Clopper–Pearson UCB ≤ target at δ = 0.05 (Bonferroni-corrected over search steps).**
3. Conformal risk control / Learn-then-Test.

## Decision Outcome

Chosen option: **2** (simplest method with a guarantee; easy to explain; implementable by Arka in < 100 lines).

* **Unit of risk = document**: a document is "wrong" if any required field is wrong. If every document has the
  same number of required fields, document-level risk ≥ field-level risk, so certifying document-level ≤ 1 %
  also certifies the §2 field-level headline. Field-level risk is still reported.
* Report two numbers: `automation_rate_at_1pct_empirical` and `automation_rate_at_1pct_certified`.
* Every accuracy/coverage number in `EVAL_REPORT.md` carries a 95 % CI (Clopper–Pearson for proportions;
  document-cluster bootstrap, 2 000 resamples, for field-level metrics and ECE).
* **Calib size target:** ≥ 1 500 synthetic + ≥ 300 T2 composite documents in `calib`.
* **T3 enlarged to 100 documents**, split 30 `T3-calib` / 70 `T3-test` (stratified by style and doc_type),
  so calibration under real-handwriting shift can be measured. (≈ 8–10 h of writing at 35–40 h/week capacity.)
* **Eval gate redesign (§11):** a 30-doc live gate with a "2-point drop" threshold is noise (one document =
  3.3 points). Instead:
  * **Replay mode (default, free):** baseline runs store raw model outputs per item. PRs that touch
    `rules/`, `core/validation`, `core/confidence`, `core/matching` re-score **cached outputs on the full
    T0 + T2-test** (thousands of docs, zero API cost). Fail if the certified automation rate drops or any
    critical-field accuracy CI upper bound falls below the baseline point estimate.
  * **Live mode (only for `prompts/` and model-adapter changes):** paired comparison on a fixed 30-doc set;
    fail if ≥ 2 more documents become wrong than baseline (count, not percent), cost cap $0.50.

### Consequences

* Good: the headline is defensible; negative results are visible instead of hidden.
* Bad: certified coverage will be lower than empirical coverage — that gap is a feature to explain.
* Bad: more calib data needed → generator handles it at no cost; T3 needs ~50 extra handwritten docs.

### Confirmation

* FS-EV-06 `clopper_pearson` and FS-CF-05 `select_threshold_sgr` unit + simulation tests (CP-11, CP-19).
* `EVAL_REPORT.md` template has CI columns; CI job fails if a metric row lacks an interval (CP-13).

## More Information

* Geifman & El-Yaniv, "Selective Classification for Deep Neural Networks", NeurIPS 2017 (arXiv:1705.08500).
* Angelopoulos et al., "Learn then Test" (2021) — alternative if multi-parameter policies are added later.
