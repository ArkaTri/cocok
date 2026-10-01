---
status: proposed
date: 2026-10-01
decision-makers: Arka
consulted: R1, R6
blueprint-sections: "§18, §10, §17"
---

# ADR-0013: Deliver through numbered checkpoints with executable gates, tags and progress logs

## Context and Problem Statement

Milestones M0/A/B/C are 1–4 weeks long. If something breaks inside a 4-week milestone, the search space for the
bug is the whole milestone. Arka also hands work to several AI agents in parallel; without a fixed contract per
step, agents drift and failures pile up ("bug massal").

Capacity is ~35–40 h/week. Summing realistic per-step estimates (see `docs/CHECKPOINTS.md`) gives ≈ 57
working days of effort; with agent parallelism the wall-clock is ≈ 11 weeks. v2.0.0's 10 weeks has **no buffer**.

## Decision Outcome

1. Work is split into **checkpoints CP-00 … CP-33**, each 0.5–2.5 days, each with: goal, owner split
   (Arka-written vs agent-written), files, docs to update, **gate script** `scripts/gates/cpNN.sh`, done-when,
   debug playbook, and git tag `cp-NN`.
2. **Gates are cumulative**: `make gates-upto CP=NN` re-runs all fast gates ≤ NN, so a regression is caught at
   the checkpoint where it was introduced; `git bisect` between `cp-*` tags isolates it.
3. **Progress log** per checkpoint: `docs/progress/CP-NN.md` (template in `docs/PROGRESS.md`) — evidence
   (command outputs, metrics), deviations, time spent. This is the monitoring surface.
4. **Calendar = 12 weeks** (Mon 2026-10-05 → Fri 2026-12-25): 10 planned weeks + slack inside Milestone B
   (≈ 3.5 days) + W12 as a full buffer/launch week.
5. **Cut line** if behind at a milestone gate (cut in this order): vendor memory (CP-32) → TrOCR arm
   (keep CRNN) → Sentry → multi-arch (arm64-only) → dashboard extras. Never cut: tests, eval report honesty,
   security baseline, backups + restore drill.

### Consequences

* Good: failures are local; agents get unambiguous contracts; progress is visible to Arka and recruiters
  (the progress logs double as a build diary for LinkedIn posts).
* Bad: overhead ≈ 20–30 min per checkpoint for the log and tag. Worth it.

### Confirmation

* CI job `checkpoint-gates` runs every gate whose tag exists on `main`.
* `docs/PROGRESS.md` table is updated in the same PR that creates a `cp-NN` tag.
