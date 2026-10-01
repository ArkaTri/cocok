# COCOK — Progress Board

Update the row in the same PR that adds `docs/progress/CP-NN.md` and pushes tag `cp-NN`.
Workflow (ADR-0014): brainstorm → AI implements → Arka studies + tests → sign-off → tag. [LC] = learning-critical.
Status: ⬜ not started · 🟨 in progress · 🟥 blocked · ✅ done (gate green + tagged) · ✂️ cut (moved to backlog)

| CP | Title | Planned week | Status | Started | Done | Hours | Gate | Log |
|---|---|---|---|---|---|---|---|---|
| 00 | Accounts, budgets, guardrails | W1 | ⬜ | | | | | |
| 01 | Monorepo skeleton + toolchain + CI | W1 | ⬜ | | | | | |
| 02 | Domain model, FSM, ports | W1 | ⬜ | | | | | |
| 03 | Money, dates, NPWP/NITKU [LC] | W1 | ⬜ | | | | | |
| 04 | Terbilang, arithmetic, tax [H] → M0 | W1 | ⬜ | | | | | |
| 05 | Data sources, licenses, manifests | W2 | ⬜ | | | | | |
| 06 | Scenario generator | W2 | ⬜ | | | | | |
| 07 | Digital renderer + bboxes | W2 | ⬜ | | | | | |
| 08 | Handwriting/composite/photo_sim | W3 | ⬜ | | | | | |
| 09 | T3 handwriting (100 docs) [H] | W2–W4 | ⬜ | | | | | |
| 10 | Dataset v0.1 | W3 | ⬜ | | | | | |
| 11 | Eval harness + metrics [H] | W3–W4 | ⬜ | | | | | |
| 12 | Baselines B4, B1a, B1b | W4 | ⬜ | | | | | |
| 13 | Baselines B2, B3, EVAL v0.1 → A | W4 | ⬜ | | | | | |
| 14 | CRNN from scratch [H] | W5 | ⬜ | | | | | |
| 15 | TrOCR + amount-reader decision | W5 | ⬜ | | | | | |
| 16 | Grounding by OCR alignment | W5 | ⬜ | | | | | |
| 17 | VLM LoRA (Qwen3.5-2B) | W6 | ⬜ | | | | | |
| 18 | Signals + calibrator [H] | W6 | ⬜ | | | | | |
| 19 | SGR policy + ablation [H] | W7 | ⬜ | | | | | |
| 20 | Adoption decisions, EVAL v0.2 → B | W7 | ⬜ | | | | | |
| 21 | DB schema + migrations | W8 | ⬜ | | | | | |
| 22 | Adapters + contract tests | W8 | ⬜ | | | | | |
| 23 | Worker pipeline | W9 | ⬜ | | | | | |
| 24 | PO matching [H] | W8 | ⬜ | | | | | |
| 25 | API + auth | W9 | ⬜ | | | | | |
| 26 | Web foundation | W8–W9 | ⬜ | | | | | |
| 27 | Review page + e2e | W10 | ⬜ | | | | | |
| 28 | POs, dashboard, about | W10 | ⬜ | | | | | |
| 29 | Observability | W9–W10 | ⬜ | | | | | |
| 30 | Deploy + auto-rollback | W10 | ⬜ | | | | | |
| 31 | Backups, security, eval gate | W11 | ⬜ | | | | | |
| 32 | Vendor memory → C | W11 | ⬜ | | | | | |
| 33 | Launch v1.0.0 | W12 | ⬜ | | | | | |

**Milestone gates:** M0 ⬜ · A ⬜ · B ⬜ · C ⬜ · v1.0.0 ⬜

---

## Template — `docs/progress/CP-NN.md`

~~~markdown
# CP-NN — <title>

| Planned | Started | Done | Hours | Tag |
|---|---|---|---|---|
| W? | YYYY-MM-DD | YYYY-MM-DD | h | cp-NN |

## What was built
- <bullet per task, link to PR>

## Evidence (paste real output, trimmed)
```text
$ make gate CP=NN
▶ ... ✔
GATE cpNN: PASS
```
- Metrics (with CIs) / screenshots / contact sheets: <links>

## Deviations from CHECKPOINTS.md
- <what changed and why; ADR link if architectural>

## Bugs found and fixed
- <symptom → root cause → test added> (also in docs/FAILURE_LOG.md if user-visible/model-related)

## Open issues carried forward
- <issue links>

## What I (Arka) learned / can now explain
- <1–3 bullets — interview material>
~~~
