# AGENTS.md — read this first

1. Read `docs/BLUEPRINT.md` §0–§3, your role brief in §19, and the ownership policy in §20.
2. Find the **current checkpoint** in `docs/PROGRESS.md` (first row that is not ✅). Work only inside it.
3. Read that checkpoint in `docs/CHECKPOINTS.md` and every FUNCTION_SPECS entry (FS-IDs) it lists.
4. **Workflow (ADR-0014):** brainstorm with Arka → you implement → Arka studies and tests → you fix → Arka signs
   off and tags. For *learning-critical* modules (`core/validation`, `core/matching`, `core/confidence`,
   `ml/calibrate`, `ml/eval/metrics`, `ml/train/crnn`) also write `docs/learning/CP-NN.md` (walkthrough, why,
   manual tests, break-it exercises, explain-back questions).
5. A checkpoint is done only when `make gate CP=NN` and `make gates-upto CP=NN` pass, the progress log is written,
   **Arka has signed off**, and tag `cp-NN` is pushed.
6. Gate failing? Follow `docs/CHECKPOINTS.md` §0.5. Never weaken a gate without an ADR.
7. Architecture/metric/contract change → update the blueprint + add an ADR + bump the blueprint version, in one PR.
8. Small PRs, one concern each, conventional commits, `ai-assisted` label when you wrote substantial code.
