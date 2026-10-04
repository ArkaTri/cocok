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
| 01 | Filled 66 config/CI/doc files; ran break-it 2, 3, 4, 6 in a scratch copy; drafted the test record and explain-back answers at my request | Built the 93-folder / 373-file structure myself; ran setup + gates on my Mac; did break-it 1; created the GitHub repo and checked CI; found 5 issues (wrong guide step, zsh comments, index.lock, cSpell, empty workflows); removed the AI co-author trailer from history. Still mine: break-it 5, rewriting the answers in my own words |
| 02 | Proposed 6 design decisions with reasons; after my approval filled 17 files (models, errors, ports, schema export, 273 tests, gate); ran the break-it table before handing over | Asked for the reasoning behind every decision; *(to fill: what I tested, own test cases, what I changed)* |
