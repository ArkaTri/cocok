---
status: "{proposed | accepted | rejected | deprecated | superseded by ADR-NNNN}"
date: YYYY-MM-DD
decision-makers: Arka
consulted: "{agent roles consulted, e.g. R1, R3}"
blueprint-sections: "{e.g. §6.1, §8}"
---

# ADR-NNNN: {short title, imperative, e.g. "Use Postgres as the job queue"}

## Context and Problem Statement

{2–5 sentences. What forces are at play? What breaks or costs too much if we do nothing?
Link evidence: benchmark numbers, error logs, release notes, issue links.}

## Decision Drivers

* {driver 1, e.g. "fits a 2 GB host"}
* {driver 2, e.g. "Arka must be able to explain it in an interview"}

## Considered Options

1. {option A}
2. {option B}
3. {option C}

## Decision Outcome

Chosen option: **{option}**, because {one-paragraph justification tied to the drivers}.

### Consequences

* Good: {…}
* Bad: {…} — mitigation: {…}

### Confirmation

{How we will know the decision was implemented and still holds: a test, a CI check,
an import-linter contract, a metric threshold, a checkpoint gate (CP-NN).}

## Pros and Cons of the Options

### {option A}
* Good, because …
* Bad, because …

### {option B}
* Good, because …
* Bad, because …

## More Information

{Links, sources (with access date), follow-ups, date to revisit.}
