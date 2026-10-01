---
status: proposed
date: 2026-10-01
decision-makers: Arka
consulted: R5, R7
blueprint-sections: "§13 (Platform), §15 (CI/CD)"
---

# ADR-0011: Harden the CI supply chain (SHA-pinned actions, least privilege, zizmor, native arm64 runners)

## Context and Problem Statement

In March 2026 attackers force-pushed **75 of 76 tags of `aquasecurity/trivy-action`** (and 7 tags of
`setup-trivy`) to credential-stealing commits; a malicious trivy binary release was also published.
Any workflow using `@v0.x` tags exfiltrated its secrets. Our CI will hold AWS OIDC role access and
LLM API keys for the eval gate. v2.0.0 lists Trivy and Dependabot but no rules for *how* actions are referenced.

Separately, GitHub-hosted **arm64 Linux runners are free for public repositories** (GA 2025-08), so multi-arch
images no longer need slow QEMU emulation.

## Decision Drivers

* A compromised third-party action must not be able to reach cloud credentials or API keys.
* Keep using standard tools (Trivy, Dependabot) — the fix is *how* we consume them.

## Considered Options

1. Tags (`@v4`) as in most tutorials.
2. **Full commit SHA pins + Dependabot for SHA updates + `permissions: {}` default + per-job minimal
   permissions + `zizmor` audit + `step-security/harden-runner` (egress audit) + OIDC only (no static cloud keys)
   + secrets only in jobs that need them + `pull_request` (never `pull_request_target`).**
3. Self-hosted runners.

## Decision Outcome

Chosen option: **2**.

* Trivy stays (Trivy CLI ≥ the advisory's safe versions, invoked via SHA-pinned action) — alternative: Grype.
* Multi-arch build: matrix of native `ubuntu-24.04` (amd64) and `ubuntu-24.04-arm` (arm64) runners, then
  `docker buildx imagetools create` to merge the manifest. (If the repo is private, arm64 runners are billed —
  then build arm64 only.)
* Eval-gate job: runs only on PRs from the same repo; API keys exposed via environment protection rules.

### Consequences

* Good: tag-poisoning attacks fail; blast radius of any compromised step is small.
* Bad: SHA pins are less readable → add `# vX.Y.Z` comments; Dependabot keeps them fresh.
* Note: SHA pinning alone does not prove provenance (orphan-commit trick). Least privilege + harden-runner +
  OIDC are the actual containment.

### Confirmation

* CP-01 gate: `zizmor .github/workflows` reports no high findings; a grep check fails CI if any `uses:` line is
  not a 40-char SHA.
* CP-30 gate: image manifest lists `linux/amd64` and `linux/arm64`.

## More Information

* https://github.com/aquasecurity/trivy/security/advisories/GHSA-69fq-xp46-6x23
* https://thehackernews.com/2026/03/trivy-security-scanner-github-actions.html
* https://github.blog/changelog/2025-08-07-arm64-hosted-runners-for-public-repositories-are-now-generally-available/
