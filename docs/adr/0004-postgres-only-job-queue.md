---
status: proposed
date: 2026-10-01
decision-makers: Arka
consulted: R1, R3, R5
blueprint-sections: "§6, §8, §9 (Jobs), §12 (Health), §15"
---

# ADR-0004: Use PostgreSQL as the only stateful service (queue = Procrastinate); drop Redis and arq

## Context and Problem Statement

v2.0.0 uses Redis + **arq** for the job queue, Redis for the worker heartbeat, and Postgres for everything else
(including the LangGraph checkpointer). Facts as of 2026-10-01:

* arq's README states: **"arq is in maintenance only mode"** (issue #510). Starting a new project on a library
  that has stopped feature development is avoidable debt.
* The production host is a single `t4g.small` (2 GB RAM). Every extra daemon competes with Postgres and the
  worker (which holds the ONNX amount reader + OCR models).
* Redis 8 is AGPLv3 (or Valkey as the BSD fork) — another license and image to track.
* Our throughput is tiny (tens to hundreds of documents/day). Postgres `SELECT … FOR UPDATE SKIP LOCKED`
  queues handle thousands of jobs/second.
* Postgres already holds the state we must keep consistent with jobs (`documents.status`). A job enqueued in
  the **same transaction** as the status change removes a whole class of "row says QUEUED but no job exists" bugs.

## Decision Drivers

* Fewer moving parts on a 2 GB host; one backup covers everything (§14).
* Transactional enqueue (exactly-once *intent*), idempotent execution.
* Maintained library with retries, locks, periodic tasks, cancellation, asyncio.
* One Postgres driver everywhere.

## Considered Options

1. Keep Redis + arq.
2. Redis/Valkey + Taskiq or Dramatiq.
3. **Postgres + Procrastinate** (v3.10, 2026-09-23, production/stable, asyncio, retries, queueing locks, periodic tasks).
4. Hand-rolled `SKIP LOCKED` queue table.

## Decision Outcome

Chosen option: **3 — Procrastinate on Postgres**, with **psycopg 3** as the single driver for SQLAlchemy
(`postgresql+psycopg://`), Procrastinate, and `langgraph-checkpoint-postgres`.

* Enqueue happens inside the same DB transaction that moves `documents.status` to `QUEUED`.
* Job lock key = `sha256(document) + pipeline_version` (Procrastinate `queueing_lock`) → duplicate uploads
  cannot create duplicate jobs.
* Retries: Procrastinate `RetryStrategy` with exponential backoff, only for exceptions marked retryable
  (`cocok_core.errors.RetryableError`).
* Worker heartbeat: a `worker_heartbeats` row updated every 15 s (or Procrastinate's worker table if
  available in the pinned version); `/readyz` checks it is fresher than 60 s.
* Rate limiting (auth/upload) is in-process (single API replica) — documented limitation; move to Caddy
  or a Postgres-backed limiter if we ever run >1 replica.

### Consequences

* Good: one stateful service; −1 container; transactional enqueue; one backup; one driver.
* Good: interview story — "I removed a component and the system got more correct."
* Bad: no Redis on the CV keyword list. Mitigation: the portability section explains the trade-off; Redis
  can be re-added behind the same `JobQueue` port if load ever requires it.
* Bad: queue load lands on Postgres. At our volume this is negligible; monitor `procrastinate_jobs` size and
  vacuum (CP-29 dashboard shows queue depth).

### Confirmation

* `import-linter` contract: nothing imports `redis` or `arq` (CP-01 config, enforced from CP-23).
* CP-23 gate: integration test enqueues inside a transaction, rolls back, and asserts **no job** exists;
  commits and asserts **exactly one** job exists even if enqueued twice.
* CP-30 gate: `docker stats` on prod shows total RSS < 1.6 GB at idle.

## Pros and Cons of the Options

### 1. Redis + arq
* Good, because familiar, fast.
* Bad, because maintenance-only; extra service; non-transactional enqueue.

### 2. Redis/Valkey + Taskiq/Dramatiq
* Good, because maintained, popular.
* Bad, because still an extra stateful service and non-transactional enqueue.

### 4. Hand-rolled queue
* Good, because maximal learning, zero deps.
* Bad, because retries, locks, scheduling, stalled-job recovery are easy to get subtly wrong.

## More Information

* https://github.com/python-arq/arq/blob/main/README.md ("maintenance only mode")
* https://pypi.org/project/procrastinate/ (3.10.0, 2026-09-23)
* PostgreSQL docs: `SELECT … FOR UPDATE SKIP LOCKED`
