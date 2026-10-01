---
status: proposed
date: 2026-10-01
decision-makers: Arka
consulted: R1, R3
blueprint-sections: "§6.1, §6.2"
---

# ADR-0005: The document state machine owns human review; the LangGraph run ends at `decide`

## Context and Problem Statement

v2.0.0 makes `decide → NEEDS_REVIEW` a **LangGraph interrupt** that resumes on human action. Human review can
take hours or days. During that time we will deploy new code many times.

LangGraph's own backward-compatibility guide says renaming/removing a node, or renaming/removing/tightening a
state key, **breaks threads that are paused** at or before that node. So every paused review becomes a migration
hazard tied to graph internals.

Worse, the system would have **two sources of truth** for "where is this document?": `documents.status` (§6.2)
and the checkpointed graph thread. When they disagree (crash between the two writes, manual DB fix, restore
from backup) there is no rule for which one wins.

## Decision Drivers

* One source of truth for document lifecycle.
* Deploys must never strand in-flight reviews.
* Keep LangGraph where it adds value: typed node pipeline, durable step-level checkpoints, retry/resume after
  a worker crash without paying for the LLM call twice.

## Considered Options

1. LangGraph interrupt for review (v2.0.0).
2. **Graph run = processing only (`ingest … decide → persist → emit_events`). Review/approve/reject/post are
   service-layer use cases driven by the domain FSM in `cocok_core.models.status`.**
3. Drop LangGraph entirely; plain Python pipeline.

## Decision Outcome

Chosen option: **2**.

* Thread id = `f"{document_id}:{pipeline_version}"`. The checkpointer gives crash-resume *within* a run.
* `decide` returns `AUTO_APPROVED` or `NEEDS_REVIEW`; `persist` writes the result and the FSM transition in one
  transaction; the thread is then **finished** (checkpoints prunable after 7 days).
* `POST /documents/{id}/approve` calls `ApproveDocument` service → `transition(status, Event.APPROVE)` →
  writes audit log → enqueues `post_document` job if needed. No graph resume.
* Re-processing (e.g., after a prompt change) = a **new** thread with the new `pipeline_version`.

### Consequences

* Good: deploys are safe; one lifecycle authority; review logic is plain, testable domain code.
* Good: still demonstrates LangGraph durable execution (where it matters: paid model calls).
* Bad: no "HITL via interrupt" demo. Mitigation: `docs/ARCHITECTURE.md` explains why interrupts are the wrong
  tool for multi-day queues — this argument is itself a strong interview answer.

### Confirmation

* Unit tests: every FSM transition in §6.2 allowed; every other pair raises `InvalidTransition` (CP-02).
* Integration test: kill the worker after `extract` checkpoint, restart → run resumes at `read_amount` and the
  LLM adapter is **not** called again (recorded-call counter == 1) (CP-23).
* Grep gate: no `interrupt(` in `apps/worker` (CP-23).

## Pros and Cons of the Options

### 1. LangGraph interrupt
* Good, because idiomatic LangGraph HITL demo.
* Bad, because paused threads couple review to graph internals; dual source of truth.

### 3. No LangGraph
* Good, because simplest.
* Bad, because we would re-implement step checkpointing; loses a skill target employers list.

## More Information

* https://docs.langchain.com/oss/javascript/langgraph/backward-compatibility
* https://docs.langchain.com/oss/python/langgraph/interrupts
* LangGraph 1.2.x (PyPI, 2026-09-21)
