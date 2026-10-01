---
status: accepted
date: 2026-10-01
decision-makers: Arka
consulted: R1
blueprint-sections: "§0, §19, §20, CHECKPOINTS §0"
supersedes: "blueprint v2.1 §20 'HUMAN-OWNED modules' policy"
---

# ADR-0014: AI implements every checkpoint; Arka brainstorms, studies, tests and signs off

## Context and Problem Statement

Blueprint v2.1 §20 reserved the core modules (validation, matching, confidence, metrics, CRNN) for Arka to write
by hand, with agents limited to specs and tests. After CP-03's tests-first step, Arka decided on a different
working model: **we brainstorm together → the AI implements → Arka studies and tests every stage.** Per §0, an
explicit instruction from Arka overrides the blueprint; §20 itself required an ADR for any override.

## Decision Drivers

* Arka's chosen workflow and time budget (~35–40 h/week).
* Keep the original goal of §20: Arka must be able to **explain, debug and defend** the core logic in interviews.
* Honesty: the portfolio must not claim hand-written code that was AI-written.

## Considered Options

1. Keep §20 (Arka hand-writes the core).
2. **AI implements everything; core modules become "learning-critical" with extra verification by Arka.**
3. AI implements everything with no extra verification.

## Decision Outcome

Chosen option: **2**.

Once, before CP-01: **Arka builds the full architecture himself in VS Code** — every folder and every file of
blueprint §7 as an empty placeholder (93 folders, 373 files, 2026-10-01). The AI never adds or moves files on its
own; it fills the placeholders that belong to the current checkpoint.

Per checkpoint:
1. **Brainstorm** (Arka + Claude): approach, trade-offs, open questions — short, before code.
2. **Implement** (AI): fills the checkpoint's placeholder files directly in the repo (Arka reviews with `git diff`); gate green; agent evidence in `docs/progress/CP-NN.md`.
3. **Learn** (Arka): study guide `docs/learning/CP-NN.md` — walkthrough, concepts, "why" decisions.
4. **Test** (Arka): run the gate, try the manual exercises, add own test cases, try to break the code; report
   findings → AI fixes (bug-fix protocol, blueprint §10).
5. **Sign-off** (Arka): fill "What I tested / learned" in the progress log → merge → tag `cp-NN`.

"Learning-critical" modules (formerly human-owned): `core/validation`, `core/matching`, `core/confidence`,
`ml/calibrate`, `ml/eval/metrics`, `ml/train/crnn`. For these, sign-off additionally requires that Arka:
* answers the guide's explain-back questions in his own words (in the progress log), and
* adds at least 3 test cases of his own (or finds a bug) for the checkpoint.

### Consequences

* Good: faster delivery; Arka spends time on understanding and verification instead of typing.
* Bad: less muscle memory of writing the core. Mitigation: explain-back + own tests + "break-it" exercises.
* Honesty rule: `docs/HOW_I_USED_AI.md` and interviews state that the AI implemented the code and Arka designed
  decisions with it, verified, tested and can explain it. Never present AI-written code as hand-written.

### Confirmation

* Every `cp-NN` tag created after this ADR has a progress log with Arka's "What I tested / learned" section filled.
* Blueprint §20 rewritten (v2.2.0); `AGENTS.md` rule 4 updated.
