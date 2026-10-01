# Contributing

1. Read `AGENTS.md`, then the current checkpoint in `docs/CHECKPOINTS.md`.
2. Branch `cp/NN-short-slug`; small PRs, one concern each; squash merge.
3. Conventional commits: `feat(core): …`, `fix(api): …`, `docs: …`, `test(core): …`, `chore(ci): …`.
4. Before pushing: `make verify` and `make gate CP=NN`.
5. Workflow (ADR-0014): brainstorm → AI implements → Arka studies and tests → sign-off. Learning-critical modules
   (blueprint §20) also get a study guide in `docs/learning/`.
6. PRs with substantial AI-generated code carry the `ai-assisted` label.
7. Bug fixes follow the protocol in blueprint §10 (failing test first; FAILURE_LOG entry when relevant).
