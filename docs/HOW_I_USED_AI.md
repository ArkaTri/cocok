# How I used AI in Cocok

*Honest account, kept current per checkpoint (blueprint §17, §20; ADR-0014).*

## Working model

1. **Brainstorm (me + Claude):** problem framing, architecture, trade-offs, and a critique of my own blueprint
   (v2.0 → v2.1: model refresh, certified abstention, Postgres-only queue, grounding by OCR alignment, …).
2. **Implement (AI agent):** code, tests, docs, CI — every checkpoint ends with an executable gate.
3. **Study (me):** a study guide per checkpoint (`docs/learning/`) — walkthrough, concepts, why each choice.
4. **Test (me):** I run the gates, test by hand, add my own test cases, and try to break the code.
5. **Sign-off (me):** I record what I tested and learned in `docs/progress/CP-NN.md` before the checkpoint is tagged.

## What is AI-written

All source code, tests and most documentation drafts. Decisions recorded as ADRs were made by me after discussion.

## Per checkpoint

| CP | AI did | I decided / tested / changed |
|---|---|---|
| 00 | — | Accounts, budgets, ADR decisions *(pending)* |
| 01 | Monorepo config, toolchain, CI (I built the folder structure myself) | *(to fill after my testing)* |
