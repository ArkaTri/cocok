# Security

## Reporting a vulnerability

Please do **not** open a public issue. Email the maintainer (see the GitHub profile of the repository owner) with
steps to reproduce. You will get an acknowledgement within 7 days.

## Baseline

Cocok targets OWASP ASVS Level 1 and the OWASP Top 10 for LLM Applications (blueprint §13). The threat model
(STRIDE-lite) is reviewed at the end of each milestone and summarized here from CP-31.

## Supply chain

GitHub Actions are pinned to commit SHAs, workflows run with least-privilege permissions, and `zizmor`,
`gitleaks` and `pip-audit` run in CI (ADR-0011).
