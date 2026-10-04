# COCOK — Checkpoint Plan (CP-00 … CP-33)

```yaml
doc_id: cocok-checkpoints
version: 1.0.0
blueprint_version: 2.1.0
adr: ADR-0013
calendar: "Mon 2026-10-05 → Fri 2026-12-25 (12 weeks; capacity ~35–40 h/week)"
status: proposed
```

This file answers **"what do I build next, how do I know it works, and what do I do when it doesn't?"**
The blueprint says *what/why*; `FUNCTION_SPECS.md` says *what each function must do*; this file says *in which
order, by whom, and how it is verified*.

---

## 0. Checkpoint protocol (read once; applies to every checkpoint)

### 0.1 Anatomy of a checkpoint

Every checkpoint below has the same fields:

| Field | Meaning |
|---|---|
| **Header row** | Milestone · planned week · effort (working days of 7–8 h) · owner · depends on · git tag |
| **Goal** | One sentence. If you cannot say it in one sentence, the checkpoint is too big. |
| **Tasks** | Numbered, each tagged with an owner (legend in §0.4). Each task ≈ one PR (≤ 1 day). |
| **Files** | The only paths this checkpoint should create/modify. Touching others needs a reason in the PR. |
| **Specs** | FUNCTION_SPECS IDs implemented here. Docstrings reference these IDs. |
| **Docs** | Documents created/updated in this checkpoint. |
| **Gate** | Commands in `scripts/gates/cpNN.sh`. Every step prints its name; the script ends with `GATE cpNN: PASS`. |
| **Done when** | Human-checkable acceptance criteria (in addition to the gate). |
| **Debug playbook** | Most likely failures for *this* checkpoint → first checks → fix. |

### 0.2 Lifecycle of one checkpoint

Workflow (ADR-0014): **brainstorm together → AI implements → Arka studies → Arka tests → AI fixes → Arka signs off.**

```
1. Brainstorm       Arka + Claude agree the approach and open questions for this checkpoint (short, before code)
2. Entry check      make gates-upto CP=<previous>        # everything before is still green
3. Branch           git switch -c cp/NN-short-slug
4. Tests first      acceptance tests from FUNCTION_SPECS (marked @pytest.mark.cpNN), then the implementation
5. Implement        AI: code + docs; CI green per commit
6. Gate             make gate CP=NN  → GATE cpNN: PASS ; make gates-upto CP=NN
7. Agent log        docs/progress/CP-NN.md: what was built, evidence, deviations
8. Study guide      docs/learning/CP-NN.md (mandatory for learning-critical modules; short for others)
9. Arka tests       gate on his machine, manual exercises, own test cases, break-it attempts → findings
10. Fix             AI fixes findings (bug-fix protocol, blueprint §10) and re-runs the gate
11. Sign-off        Arka fills "What I tested / learned" in the log → merge to main → tag cp-NN → board
```

### 0.3 Gate mechanics (implemented in CP-01; used by every later checkpoint)

* `scripts/gates/_lib.sh` provides `step "<name>" <command…>` (prints `▶ <name>`, runs, prints `✔`/`✘` with
  duration, exits non-zero on failure) and `pass cpNN`.
* `scripts/gates/cpNN.sh` — one per checkpoint, `set -euo pipefail`, **fast** (target < 3 min; slow steps are
  marked `SLOW=1` and skipped by `gates-upto` unless `FULL=1`).
* Acceptance tests carry a pytest marker per checkpoint: `@pytest.mark.cp03`. Gate scripts run
  `uv run pytest -m cp03`, so a failing gate points at the checkpoint whose contract broke. A gate never runs
  tests of a *later* checkpoint, so tests-first branches (red tests for CP-N+1) cannot break gate N.
* Tests-first work for `[H+T]` checkpoints lives on the branch `cp/NN-slug` until it is green; `main` stays green.
* `make gate CP=NN` runs one gate; `make gates-upto CP=NN` runs every gate `cp00..cpNN` (fast steps).
* CI workflow `checkpoint-gates.yml` runs `gates-upto` for the highest `cp-*` tag reachable from `main`.

Example (shape only — R6 writes the real scripts):

```bash
#!/usr/bin/env bash
# Gate CP-03 — money, dates, NPWP/NITKU normalizers [HUMAN]
set -euo pipefail
source "$(dirname "$0")/_lib.sh"
step "acceptance tests (cp03)"      uv run pytest -m cp03 -q
step "doctests: validation"         uv run pytest --doctest-modules packages/core/src/cocok_core/validation -q
step "coverage >= 90% (validation)" uv run pytest -m cp03 -q --cov=cocok_core.validation --cov-fail-under=90
step "mypy strict (core)"           uv run mypy packages/core
pass cp03
```

### 0.4 Owner legend

| Tag | Meaning |
|---|---|
| **[H]** | Human-only task (account setup, handwriting, buying forms, decisions). |
| **[H+T]** | *(since ADR-0014)* Learning-critical: the AI writes tests first, then the implementation and a study guide; Arka studies, tests (incl. ≥ 3 own test cases) and answers explain-back questions before sign-off. |
| **[A:Rn]** | Agent with role Rn implements; Arka reviews the PR and must be able to explain it. |
| **[H✓]** | Arka decision/approval required (ADR acceptance, adoption decision, publish). |

**Reading older task lines (ADR-0014):** inside learning-critical checkpoints, task lines written as
"[H] Implement …" are now done by the AI; Arka's part is to study, test (≥ 3 own test cases), answer the
explain-back questions and sign off. "[H]" stays literal for human-only tasks (accounts, handwriting, decisions).

Parallelism rule: at most **two** agent tracks open at once, so Arka's review load stays ≤ ~3 h/day.

### 0.5 When a gate fails — debugging protocol

1. **Read the first `✘` line.** The step name tells you which contract broke. Do not scroll to the last error.
2. **Re-run only that step** (copy its command). Add `-x -vv --lf` for pytest; `--hypothesis-show-statistics`
   for property tests.
3. **Is it this checkpoint or an earlier one?** `make gates-upto CP=<NN-1>`. If an earlier gate fails, the bug
   was introduced by a change that slipped past that gate → fix there first.
4. **Bisect between tags** when the cause is not obvious:
   `git bisect start HEAD cp-<NN-1> && git bisect run make gate CP=NN` (gates are deterministic by design).
5. **Bug-fix protocol (§10 of blueprint):** reproduce → failing test → minimal fix → suite green →
   `docs/FAILURE_LOG.md` entry with *checkpoint where introduced* → separate PR.
6. **Stuck > 2 hours?** Write the symptom, what you tried, and the smallest reproducer into the progress log and
   ask (agent R1 or Claude). Never "fix" a gate by weakening it without an ADR.

### 0.6 Definition of Done (applies to every checkpoint, in addition to its own list)

* Gate passes locally **and** in CI; `gates-upto` green.
* New/changed public functions have Google-style docstrings with their FS-ID; `core` examples run as doctests.
* No `TODO` without an issue link. No secrets in the diff (gitleaks green).
* Progress log written; `docs/PROGRESS.md` updated; tag pushed.
* If behavior/architecture changed: blueprint/ADR/FUNCTION_SPECS updated in the same PR.

### 0.7 Makefile contract (CP-01 creates these targets; later checkpoints only add to them)

| Target | Does |
|---|---|
| `make setup` | `uv sync --all-packages`, `corepack enable && pnpm install` (once web exists), `pre-commit install` |
| `make lint` | `ruff check .`, `ruff format --check .`, `lint-imports` |
| `make type` | `mypy packages/core packages/adapters` (strict) |
| `make test` | `pytest -q -m "not integration and not slow"` |
| `make test-core` | `pytest packages/core --doctest-modules --cov=cocok_core --cov-fail-under=90` |
| `make test-int` | `pytest -q -m integration` (testcontainers) |
| `make gate CP=NN` | `bash scripts/gates/cpNN.sh` |
| `make gates-upto CP=NN` | every gate ≤ NN (fast steps) |
| `make eval ROUTE=… TIERS=…` | `cocok-eval run …` (added in CP-11) |
| `make replay FROM=…` | `cocok-eval replay …` (added in CP-11) |
| `make web-check` | `pnpm -C apps/web typecheck lint test build` (added in CP-26) |
| `make e2e` | Playwright critical path (added in CP-27) |

### 0.8 Overview and calendar

| CP | Title | Milestone | Week (2026) | Effort (d) | Owner | Depends on |
|---|---|---|---|---|---|---|
| 00 | Accounts, budgets, guardrails | M0 | W1 Oct 5 | 0.5 | H | — |
| 01 | Monorepo skeleton + quality toolchain + CI | M0 | W1 | 1 | A:R1/R5 | 00 |
| 02 | Domain model, FSM, ports | M0 | W1 | 1 | A:R3 | 01 |
| 03 | Money, dates, NPWP/NITKU | M0 | W1 | 1 | H+T | 02 |
| 04 | Terbilang, arithmetic, tax rules → **M0 gate** | M0 | W1 | 1.5 | H+T | 03 |
| 05 | Data sources, licenses, manifests, leakage check | A | W2 Oct 12 | 1 | A:R2 + H | 01 |
| 06 | Scenario generator core | A | W2 | 1.5 | A:R2 | 04, 05 |
| 07 | Digital renderer + bbox ground truth | A | W2 | 1.5 | A:R2 | 06 |
| 08 | Handwriting-like, composite, photo_sim renderers | A | W3 Oct 19 | 2 | A:R2 | 07 |
| 09 | T3 handwriting collection (100 docs) | A | W2–W4 (spread) | 2 | H | 06 |
| 10 | Dataset v0.1 assembly (tiers, calib, card, HF) | A | W3 | 1.5 | A:R2 + H✓ | 08 |
| 11 | Eval harness v1 + metrics | A | W3–W4 | 2 | A:R2 + H+T | 10 |
| 12 | Baselines B4 (digital) + B1a/B1b (OCR-VLM) | A | W4 Oct 26 | 1.5 | A:R2 | 11 |
| 13 | Baselines B2 + B3, EVAL_REPORT v0.1 → **A gate** | A | W4 | 2 | A:R2 + H | 12, 09 |
| 14 | CRNN amount reader from scratch | B | W5 Nov 2 | 2 | H+T | 13 |
| 15 | TrOCR fine-tune + amount-reader decision | B | W5 | 1.5 | A:R2 + H✓ | 14 |
| 16 | Grounding by OCR alignment | B | W5 | 1 | A:R2/R3 | 13 |
| 17 | VLM LoRA fine-tune (Qwen3.5-2B) | B | W6 Nov 9 | 2.5 | A:R2 | 13 |
| 18 | Confidence signals + calibrator | B | W6 | 2 | H+T | 15, 16 |
| 19 | SGR policy, risk–coverage, ablation | B | W7 Nov 16 | 1.5 | H+T + A:R2 | 18 |
| 20 | Adoption decisions, EVAL_REPORT v0.2 → **B gate** (+ ≈3.5 d slack) | B | W7 | 1 | H✓ + A:R2 | 17, 19 |
| 21 | DB schema, migrations, repositories | C | W8 Nov 23 | 2 | A:R3 | 20 |
| 22 | Adapters + contract tests | C | W8 | 2 | A:R3 | 21 |
| 23 | Worker pipeline (Procrastinate + LangGraph) | C | W9 Nov 30 | 2.5 | A:R3 | 22 |
| 24 | PO matching (incl. three-way) | C | W8 (parallel) | 1.5 | H+T | 04 |
| 25 | API: auth/sessions/CSRF/RBAC, documents, review | C | W9 | 2.5 | A:R3/R7 | 23, 24 |
| 26 | Web foundation: login, upload, queue | C | W8–W9 | 2 | A:R4 | 25 (OpenAPI draft) |
| 27 | Review page with grounding + Playwright critical path | C | W10 Dec 7 | 2.5 | A:R4 | 26 |
| 28 | Purchase orders, dashboard, about | C | W10 | 1.5 | A:R4/R6 | 27 |
| 29 | Observability | C | W9–W10 | 1.5 | A:R5 | 23 |
| 30 | Containers, EC2, OIDC, deploy + auto-rollback | C | W10 | 2.5 | A:R5 | 25, 29 |
| 31 | Backups + restore drill, security review, eval-gate CI | C | W11 Dec 14 | 1.5 | A:R5/R7/R6 | 30 |
| 32 | Vendor memory (SHOULD) → **C gate** | C | W11 | 1.5 | A:R3 | 31 |
| 33 | Launch: docs, video, release v1.0.0 (+ buffer week) | L | W12 Dec 21 | 1.5 | H + A:R8 | 32 |

Sum of effort ≈ 57 working days; with two agent tracks in parallel the wall-clock fits W1–W11, leaving W12 as
buffer/launch and ≈ 3.5 days of slack in W7. **Cut line** if behind at a milestone gate (in order): CP-32 →
TrOCR arm of CP-15 → Sentry (CP-29) → multi-arch (arm64-only) → dashboard extras (CP-28).
**Never cut:** tests, CIs in the eval report, security baseline, backups + restore drill.

---

# Milestone M0 — Foundation (W1: 2026-10-05 → 10-09)

## CP-00 — Accounts, budgets, guardrails

| Milestone M0 | W1 Mon | 0.5 d | Owner: H | Depends: — | Tag: `cp-00` |
|---|---|---|---|---|---|

**Goal.** Every external account, key and spending guard exists before a single line of code.

**Tasks.**
1. [H] GitHub repo `cocok` (public per D9), branch protection on `main` (PR required, status checks required once CP-01 adds them, no force-push).
2. [H] AWS: Budget with alerts at 50/80/100 % of US$25/month (email); Cost Anomaly Detection on; confirm Free Plan end date and credit balance in Billing; complete the "Budget" credit activity first. Region decision D8: compare `t4g.small` price in ap-southeast-1 vs ap-southeast-3 in the Pricing Calculator, include public IPv4 hourly charge.
3. [H] Accounts + tokens (store in a password manager, never in git): Hugging Face (fine-grained write token), Kaggle (API token; phone-verify for GPU; note the weekly GPU quota shown in settings), Langfuse Cloud project, OpenAI / Gemini / Bedrock access, Modal (free credits), Sentry (optional).
4. [H] Local toolchain on the Mac: `uv`, `pnpm` (via `corepack`), Docker (Docker Desktop or OrbStack), `gh`, `make`, `git ≥ 2.40`.
5. [H✓] Read ADR-0003…0013; accept/reject each (D6). Rejected ADR → tell R1 to revert that part of the blueprint before CP-01.

**Files.** None in repo yet (log is committed in CP-01 as `docs/progress/CP-00.md`).

**Docs.** `docs/progress/CP-00.md` (accounts created, quota numbers, region decision, ADR decisions).

**Gate** (`cp00.sh`, created in CP-01, checks the machine): `uv --version` · `pnpm -v` · `docker info` · `gh auth status` · `python3 -c "import sys; assert sys.version_info >= (3,12)"`.

**Done when.** Budget alert test email received; all tokens stored; ADR decisions recorded.

**Debug playbook.**
| Symptom | Likely cause | Check / fix |
|---|---|---|
| Kaggle notebook has no GPU option | Phone not verified | Kaggle → Settings → Phone verification |
| Budget alert email never arrives | SNS/email subscription not confirmed | Confirm the subscription email; send test alert |
| `docker info` fails on macOS | Docker VM not running | Start Docker Desktop/OrbStack; `docker context ls` |

---

## CP-01 — Monorepo skeleton + quality toolchain + CI

| M0 | W1 Mon–Tue | 1 d | Owner: A:R1 (repo), A:R5 (CI) | Depends: CP-00 | Tag: `cp-01` |
|---|---|---|---|---|---|

**Goal.** An empty but fully-wired monorepo where lint, types, tests, layering, secrets and gates run locally and in CI.

**Tasks.**
1. [A:R1] uv workspace (`pyproject.toml` root; members `packages/core`, `packages/adapters`, `packages/ml`, `apps/api`, `apps/worker`); `.python-version` = `3.13`; every member `requires-python = ">=3.12"`; `src/` layout; `py.typed`; one smoke test per package.
2. [A:R1] `ruff` config (line length 100; rules E, F, I, B, UP, D (google), C90 (max 10), PL subset); `mypy --strict` for core + adapters; `import-linter` contracts: (a) `cocok_core` independent of all others, (b) `cocok_api`/`cocok_worker` must not import `cocok_ml`, (c) forbidden external imports `redis`, `arq`, `passlib`, `jose`.
3. [A:R1] pytest config: markers `cp00`…`cp33`, `integration`, `slow`; `--strict-markers`; doctest options `NORMALIZE_WHITESPACE ELLIPSIS`.
4. [A:R1] `pre-commit`: ruff, ruff-format, mypy (core), gitleaks, end-of-file-fixer, check-yaml, check-added-large-files (500 KB).
5. [A:R1] `Makefile` with the §0.7 targets; `scripts/gates/_lib.sh`, `cp00.sh`, `cp01.sh`.
6. [A:R5] Workflows `ci-python.yml`, `security.yml` (gitleaks, zizmor, pip-audit), `checkpoint-gates.yml`; every `uses:` pinned to a 40-char SHA with `# vX.Y.Z` comment; top-level `permissions: {}`; per-job minimal permissions; `harden-runner` in audit mode.
7. [A:R5] `dependabot.yml`: `github-actions` weekly; `pip` weekly for app deps, **monthly** grouped for ML deps; `npm` weekly (activated in CP-26).
8. [A:R8] `AGENTS.md`, `CLAUDE.md` (`See AGENTS.md`), README skeleton (problem, persona, headline metric), `CONTRIBUTING.md`, `CHANGELOG.md`, `SECURITY.md` stub; copy this docs package into `docs/`.
9. [H] ADR-0001 (domain choice — why Indonesian back-office reconciliation) and ADR-0002 (provider-agnostic adapters) using `docs/adr/0000-template.md`. Agents may draft; Arka edits and signs.

**Files.** `pyproject.toml`, `uv.lock`, `.python-version`, `Makefile`, `.pre-commit-config.yaml`, `.importlinter`, `packages/*/pyproject.toml`, `packages/*/src/**/__init__.py`, `apps/api|worker/pyproject.toml`, `scripts/gates/*`, `.github/workflows/*`, `.github/dependabot.yml`, root docs.

**Specs.** —  **Docs.** AGENTS.md, README, ADR-0001, ADR-0002, `docs/progress/CP-00.md`, `docs/progress/CP-01.md`.

**Gate** (`cp01.sh`):
```
step "lockfile in sync"        uv sync --all-packages --frozen
step "lint"                    make lint
step "types"                   make type
step "tests"                   make test
step "pre-commit all files"    uv run pre-commit run --all-files
step "actions pinned by SHA"   ! grep -rnE 'uses: [^@]+@(v[0-9]|main|master)' .github/workflows
step "zizmor (no high)"        uvx zizmor --min-severity high .github/workflows
step "python pins"             test "$(cat .python-version)" = "3.13"
```

**Done when.** A PR shows all CI jobs green; branch protection lists them as required; a deliberately committed fake AWS key is blocked by pre-commit (then removed).

**Debug playbook.**
| Symptom | Likely cause | Check / fix |
|---|---|---|
| `uv sync` resolution conflict | torch/ML deps pulled into the default group | Put ML deps under `packages/ml` optional extra `[train]`; CI for core/api never installs it |
| mypy cannot find `cocok_core` from adapters | workspace member not installed editable | `uv sync --all-packages`; set `mypy_path`/`explicit_package_bases` |
| `lint-imports` "module not found" | `root_packages` names don't match import names | List `cocok_core, cocok_adapters, cocok_ml, cocok_api, cocok_worker` |
| gitleaks false positive on a test fixture | Fake NPWP/NIK looks like a secret | Add fingerprint to `.gitleaksignore`, never disable the hook |
| SHA-pin grep fails on a local action (`./.github/...`) | Regex too strict | Exclude `uses: ./` lines |

---

## CP-02 — Domain model, state machine, ports

| M0 | W1 Tue–Wed | 1 d | Owner: A:R3 | Depends: CP-01 | Tag: `cp-02` |
|---|---|---|---|---|---|

**Goal.** The language of the system exists as pure, typed Python: schemas, value objects, the document FSM, errors and ports.

**Tasks.**
1. [A:R3] `Money` value object; `LineItem`, `ExtractedDocument`, `FieldMeta` (Pydantic v2, frozen) + `REQUIRED_FIELDS` per doc_type (blueprint §3.2).
2. [A:R3] `DocumentStatus`, `Event`, `transition()` (blueprint §6.2) + `InvalidTransition`.
3. [A:R3] Error hierarchy `cocok_core.errors`.
4. [A:R3] Ports (`typing.Protocol`): `Extractor`, `AmountReader`, `OcrEngine`, `Storage`, `LLMClient`, `JobQueue`, `Clock`, `IdGenerator`. *(Repository ports moved to CP-21/22, decided in CP-02: their shape depends on the DB schema.)*
5. [A:R3] JSON-schema export: `python -m cocok_core.schema_export > schemas/extracted_document.schema.json` (used later for structured outputs and prompts); golden snapshot test.
6. [A:R6] Hypothesis state-machine test: random event sequences never reach a state outside §6.2.

**Files.** `packages/core/src/cocok_core/{models,ports,errors.py,schema_export.py}`, `packages/core/tests/models/*`, `schemas/extracted_document.schema.json`.

**Specs.** FS-CM-01 … FS-CM-05.  **Docs.** docstrings; `docs/progress/CP-02.md`.

**Gate** (`cp02.sh`): lockfile · lint · `mypy` strict core · mypy on the port fakes · `pytest -m cp02` · doctests `cocok_core/models` + `errors.py` · core coverage ≥ 90 % · schema snapshot unchanged (`schema_export --check`, works without a clean git tree).

**Done when.** Every allowed transition in §6.2 is a passing test; every other `(state, event)` pair raises `InvalidTransition` (exhaustive parametrized test).

**Debug playbook.**
| Symptom | Likely cause | Check / fix |
|---|---|---|
| Schema snapshot changes on every run | Unordered dict/enum output | `json.dumps(..., sort_keys=True, indent=2)` |
| `Decimal` qty serializes as float | Pydantic default | Field serializer → string; JSON schema `type: string, pattern` |
| `Money(5.0)` or a timestamp date is accepted | `model_validate(..., strict=False)` overrides field-level `Strict()` | Never pass `strict=False`; test `test_strict_false_would_disable_the_protection` |
| Docstring text appears in the JSON schema | Pydantic copies class docstrings into `description` | Short one-line docstrings on models; `json_schema_extra` for `Money` |
| mypy complains about Protocol variance | Mutable attributes in Protocol | Use methods/properties only in ports |

---

## CP-03 — Money, dates, NPWP/NITKU normalizers  `[LEARNING-CRITICAL]`

| M0 | W1 Wed–Thu | 1 d | Owner: H+T (R6 tests first) | Depends: CP-02 | Tag: `cp-03` |
|---|---|---|---|---|---|

**Goal.** Fully tested parsers turn messy Indonesian money, date and tax-ID strings into canonical values — and Arka can explain every rule.

**Tasks.**
1. [A:R6] Failing tests from FS-CV-01…05: example tables, edge cases, Hypothesis round-trips (`parse_money(format_money(m)) == m`; `normalize_npwp` idempotent), error cases. Marker `cp03`.
2. [H] Implement `parse_money`, `format_money`, `parse_date_id`, `normalize_npwp`, `normalize_nitku` with Google docstrings + doctest examples.
3. [A:R6] Review: missing edge cases → new tests (Arka fixes).

**Files.** `packages/core/src/cocok_core/validation/{money,dates,npwp}.py`, `packages/core/tests/validation/test_{money,dates,npwp}.py`.

**Specs.** FS-CV-01 … FS-CV-05.  **Docs.** docstrings; `docs/progress/CP-03.md` (include 3 bugs Hypothesis found, if any — great interview material).

**Gate** (`cp03.sh`): see §0.3 example.

**Done when.** Arka can explain, without notes, why `"1.250"` is 1 250 but `"1.25"` is an error, and why legacy NPWP gets a leading `0`.

**Debug playbook.**
| Symptom | Likely cause | Check / fix |
|---|---|---|
| Hypothesis finds a round-trip failure | Edge: 0, very large ints, `Rp` without space | Read the *shrunk* example; add it as `@example(...)` after fixing |
| `1,250,000` parsed as 1 | Comma treated as decimal separator first | Decide separator by pattern (groups of 3), see FS-CV-01 algorithm notes |
| Date `05/10/26` parsed as May 10 | M/D/Y assumption | Indonesian is always D/M/Y — never call `dateutil.parser` with defaults |
| NPWP with spaces/dots fails | Stripping only dots | Strip every non-digit before length check |

---

## CP-04 — Terbilang, arithmetic, tax rules  `[LEARNING-CRITICAL]` → **Milestone M0 gate**

| M0 | W1 Thu–Fri | 1.5 d | Owner: H+T; A:R3 for YAML loader | Depends: CP-03 | Tags: `cp-04`, `milestone-m0` |
|---|---|---|---|---|---|

**Goal.** Numbers ↔ Indonesian words, document arithmetic and PPN rules work deterministically and are driven by versioned rule files.

**Tasks.**
1. [A:R6] Failing tests FS-CV-06…10: golden table (≥ 200 pairs incl. 11, 100, 1 000, 1 000 000, "sejuta", "milyar", glued words), Hypothesis round-trip `parse_terbilang(to_terbilang(n)) == n` for `0 ≤ n < 10^15`, arithmetic invariants, tax effective-date selection.
2. [H] Implement `to_terbilang`, `parse_terbilang`, `check_arithmetic`, `compute_ppn`, `normalize_field`/`fields_equal`.
3. [A:R3] `rules/tax.yaml`, `rules/tolerances.yaml` + Pydantic schema + loader (fails fast on invalid file); **re-verify PPN facts on pajak.go.id when writing the file** and cite the regulation + access date in the YAML comments.
4. [A:R1] Run the M0 milestone review: `gates-upto CP=04`, core coverage, threat model v0 (one page).

**Files.** `packages/core/src/cocok_core/validation/{terbilang,arithmetic,tax,fields}.py`, `rules/*.yaml`, `packages/core/src/cocok_core/rules_schema.py`, tests.

**Specs.** FS-CV-06 … FS-CV-10.  **Docs.** docstrings; `docs/progress/CP-04.md`; README "How Cocok decides" paragraph.

**Gate** (`cp04.sh`): `pytest -m cp04` · Hypothesis with `--hypothesis-profile=ci` (500 examples) · doctests · `make test-core` (≥ 90 %) · rules schema validation of every file in `rules/`.

**Done when (M0).** CI green on main; gates cp00–cp04 green; core coverage ≥ 90 %; ADR-0001/0002 merged.

**Debug playbook.**
| Symptom | Likely cause | Check / fix |
|---|---|---|
| "seribu" parsed as 1 000 000 | Scale words applied greedily | Process from the largest scale down; "se" binds to the next unit only |
| 11 000 → "satu puluh satu ribu" | Missing *belas* rule inside a group | Groups of three digits are converted by one function, reused for every scale |
| Tax off by 1 rupiah | Rounding mode | Rounding mode is a rule-file field; test both modes |
| Arithmetic fails on qty 2.5 | Float math | `Decimal(qty) * unit_price` then round per tolerance rule to int rupiah |

---

# Milestone A — Data + baselines (W2–W4: 2026-10-12 → 10-30)

## CP-05 — Data sources, licenses, manifests, leakage check

| A | W2 Mon | 1 d | Owner: A:R2 (+ H for downloads needing a login) | Depends: CP-01 | Tag: `cp-05` |
|---|---|---|---|---|---|

**Goal.** Every external dataset is downloaded, license-recorded, hashed into a manifest, and protected by an automated leakage check.

**Tasks.**
1. [H] Download sources that need a browser/login (CVL HDS, ORAND-CAR, accept Kaggle dataset rules); place raw files under `~/cocok-data/raw/<source_id>/` (outside git).
2. [A:R2] `cocok-data fetch <source_id>` for scriptable sources (Kaggle API, HF); `cocok-data manifest <source_id>` → `data/manifests/<source_id>.parquet` (FS-DG-07).
3. [A:R2] `data/LICENSES.md`: URL, license name, license text snapshot (or link + hash), access date, allowed uses (copy §4.1).
4. [A:R2] `cocok-data leakage-check` (FS-DG-08) + workflow `data-checks.yml`; negative test fixture with a planted overlap.
5. [A:R5] `pip-licenses` step in `security.yml` (fail on AGPL/GPL in default + `ml` extras).
6. [A:R2] Upload raw data to a **private** HF dataset repo (or S3 bucket) — the manifest records the remote URI.

**Files.** `packages/ml/src/cocok_ml/datagen/{sources.py,manifest.py,leakage.py}`, `data/manifests/*.parquet`, `data/LICENSES.md`, `.github/workflows/data-checks.yml`.

**Specs.** FS-DG-07, FS-DG-08.  **Docs.** `data/LICENSES.md`; `docs/progress/CP-05.md`.

**Gate** (`cp05.sh`): `pytest -m cp05` · manifests validate against schema (no null `license`/`sha256`) · `leakage-check` passes on real manifests · `leakage-check` **fails** on the planted-overlap fixture (asserted) · `pip-licenses` clean.

**Done when.** Arka can answer "which files may we publish, modify, composite?" from `LICENSES.md` alone.

**Debug playbook.**
| Symptom | Likely cause | Check / fix |
|---|---|---|
| Kaggle API 403 | Dataset rules not accepted | Open dataset page → accept → retry |
| sha256 differs between Mac and CI | Hashing a re-encoded image | Hash the **raw bytes** of the file as downloaded, never a decoded/re-saved image |
| Manifest too big for git | One row per crop × 400k | Partition parquet by source + split; keep < 50 MB per file or move to HF and commit only a pointer + hash |

---

## CP-06 — Scenario generator core

| A | W2 Tue–Wed | 1.5 d | Owner: A:R2 | Depends: CP-04, CP-05 | Tag: `cp-06` |
|---|---|---|---|---|---|

**Goal.** Seeded generation of fictional, internally consistent transactions (ground truth first), with labeled perturbations.

**Tasks.**
1. [A:R2] Config `datagen/config/v1.yaml`: fictional vendor name parts, toko bangunan item catalog (semen, pasir, besi beton, bata ringan, cat, paku, pipa PVC, keramik, triplek…) with units (sak, m³, batang, kg, kaleng, dus, lembar) and price ranges; doc-type mix; PKP vs non-PKP share.
2. [A:R2] `generate_scenario(seed, config)` (FS-DG-01) using **Arka's** `to_terbilang`, `format_money`, `compute_ppn` from `core` (no re-implementation).
3. [A:R2] `plant_perturbation(scenario, kind, rng)` (FS-DG-02) for every kind in blueprint §4.2, with labels.
4. [A:R2] `make_scenario_sheet(scenario)` (FS-DG-10) → printable A5 PDF for T3 handwriting (used by CP-09).
5. [A:R6] Validator cross-check test: Arka's `check_arithmetic` must flag 100 % of planted arithmetic perturbations and 0 % of clean scenarios.

**Files.** `packages/ml/src/cocok_ml/datagen/{scenario.py,perturb.py,sheet.py,config/v1.yaml}`, tests.

**Specs.** FS-DG-01, FS-DG-02, FS-DG-10.  **Docs.** `docs/progress/CP-06.md` with a distribution report (doc types, amount histogram, perturbation counts).

**Gate** (`cp06.sh`): determinism (same seed → identical canonical-JSON sha256, 3 runs) · 1 000 scenarios validate against `ExtractedDocument` · planted-perturbation recall = 100 %, false-positive = 0 % (clean) · all NPWP/NIK/NITKU generated pass `normalize_*` structurally.

**Done when.** Arka prints 5 scenario sheets and they read like plausible Indonesian transactions.

**Debug playbook.**
| Symptom | Likely cause | Check / fix |
|---|---|---|
| Non-deterministic output | Iterating a `set`, unseeded `random`, time-based values | Use one `numpy.random.Generator` passed explicitly; sort sets; dates from rng, never `today()` |
| Totals off by a few rupiah | Float math in generator | `Decimal` qty, int rupiah, the same rounding helper as `core` |
| Validator misses a planted error | Perturbation within tolerance | Perturbation magnitudes must exceed `rules/tolerances.yaml`; assert in generator |

---

## CP-07 — Digital renderer + bbox ground truth

| A | W2 Wed–Thu | 1.5 d | Owner: A:R2 | Depends: CP-06 | Tag: `cp-07` |
|---|---|---|---|---|---|

**Goal.** Scenarios render to realistic text-layer PDFs (and page PNGs) with exact per-field bounding boxes.

**Tasks.**
1. [A:R2] Jinja2 HTML templates: invoice / faktur-style, purchase order, printed surat jalan, printed kwitansi; every field wrapped in `<span data-field="…">`.
2. [A:R2] `render_digital(scenario, template, out)` (FS-DG-03): HTML → PDF (WeasyPrint or Playwright Chromium; choose one, ADR if Chromium), extract field boxes, convert to **page-normalized, top-left origin** coordinates; rasterize pages at 200 DPI with `pypdfium2`.
3. [A:R2] Bundle OFL-licensed fonts in `assets/fonts/` (list licenses in `data/LICENSES.md`).

**Files.** `packages/ml/src/cocok_ml/datagen/render_digital.py`, `packages/ml/src/cocok_ml/datagen/templates/*.html.j2`, `assets/fonts/*`.

**Specs.** FS-DG-03.  **Docs.** `docs/progress/CP-07.md` + contact sheet `docs/progress/assets/cp07/*.png` (5 docs with GT boxes drawn).

**Gate** (`cp07.sh`): render 200 docs · every PDF has a text layer · for ≥ 99.5 % of fields, text extracted (pypdfium2) **inside** the GT bbox normalizes to the GT value · boxes within [0, 1] · deterministic bytes for same seed (or deterministic text + boxes if the PDF engine embeds timestamps).

**Done when.** The contact sheet shows boxes tight around every field on all 4 templates.

**Debug playbook.**
| Symptom | Likely cause | Check / fix |
|---|---|---|
| Boxes vertically mirrored | PDF origin is bottom-left; images are top-left | `y_img = page_h − y_pdf`; one conversion helper, unit-tested |
| Boxes offset by a constant | DPI mismatch (72 pt vs 200 DPI) | Normalize to [0,1] first, scale to pixels only for drawing |
| Fonts differ between Mac and CI | System font fallback | Only bundled fonts; `@font-face` with local files |
| PDF bytes differ run to run | Embedded creation date / IDs | Set fixed metadata, or compare extracted text + boxes instead of bytes |

---

## CP-08 — Handwriting-like, composite and photo_sim renderers

| A | W3 Mon–Tue | 2 d | Owner: A:R2 | Depends: CP-07 | Tag: `cp-08` |
|---|---|---|---|---|---|

**Goal.** Visual documents that look like phone photos of handwritten nota/kwitansi, with GT boxes that survive every augmentation.

**Tasks.**
1. [A:R2] `render_handwriting_like` (FS-DG-04): OFL handwriting fonts + stroke width/jitter/baseline wobble; **training only** (manifest flag `train_only=true`).
2. [A:R2] `render_composite` (FS-DG-05): paste real crops (`names`, `cvl_hds`) into blank nota/kwitansi templates; ink color + alpha blending; record bbox and `source_item_id`s; license of the result = most restrictive input (CVL → NC).
3. [A:R2] `photo_sim` (FS-DG-06, ADR-0009): torchvision v2 geometric/photometric ops + own ops (shadow gradient, paper texture, crumple displacement, low-light gamma+noise, ink bleed); boxes transformed by the same matrix/field; every op returns `params_used` → manifest `augment_params_json`.
4. [A:R2] Guard: any attempt to composite/modify an `orand_car` item raises `LicenseViolation`.

**Files.** `packages/ml/src/cocok_ml/datagen/{render_handwriting.py,render_composite.py,photo_sim.py}`, `assets/templates/blank_*.png`, tests.

**Specs.** FS-DG-04 … FS-DG-06.  **Docs.** `docs/progress/CP-08.md` + contact sheets (24 samples per renderer).

**Gate** (`cp08.sh`): determinism (seed → identical PNG hash) · bbox-mask test on 50 seeded samples (rendered field mask pixels ⊂ transformed GT box, ≥ 98 %) · license propagation test (composite with CVL crop → `CC-BY-NC-3.0`) · `orand_car` guard raises · T2-test composites use only `names`/`cvl_hds` **test** crops (asserted by `source_item_id` lookup).

**Done when.** Arka cannot immediately tell 3 of 10 random composites from real photos at thumbnail size (subjective — note it honestly in the log).

**Debug playbook.**
| Symptom | Likely cause | Check / fix |
|---|---|---|
| Boxes drift after perspective warp | Box corners not transformed with the same homography | Transform 4 corners, then take the axis-aligned hull |
| Colors look wrong | OpenCV BGR vs PIL/torch RGB | Convert once at load; assert channel order in a test |
| Composite crops look pasted | Hard alpha edges, wrong ink color | Feather mask, sample ink color from template stroke color ± noise |
| Determinism fails only on CI | Different OpenCV/torch builds | Pin versions; compare with tolerance (PSNR > 60 dB) instead of hash if needed — document it |

---

## CP-09 — T3 handwriting collection (100 documents)  `[HUMAN]`

| A | W2 Fri → W4 Tue (spread) | 2 d total | Owner: H | Depends: CP-06 (scenario sheets) | Tag: `cp-09` |
|---|---|---|---|---|---|

**Goal.** 100 real handwritten Indonesian documents with ground truth known *before* writing, split 30 calib / 70 test.

**Tasks.**
1. [A:R2] Generate 100 scenario sheets stratified by doc_type (nota 40, kwitansi 35, surat jalan 25) and style (2–3 styles), with a capture-condition plan (light: daylight / lamp / dim; angle: flat / tilted; background: table / clipboard).
2. [H] Buy real blank forms (buku nota, kwitansi, surat jalan pads) for realism.
3. [H] Write documents from sheets: batch 1 = 20 (W2 Fri), batch 2 = 40 (W3), batch 3 = 40 (W4 Mon–Tue). Photograph **immediately** after writing; rename files `T3_<scenario_id>_<condition>.jpg` the same day.
4. [A:R2] Ingest script: strip EXIF (GPS!), compute sha256, link to scenario GT, assign split (stratified 30/70 by style × doc_type, seeded).
5. [H] Annotate only the `total_amount` box (Label Studio or a small click-to-box script) — everything else is known from the scenario.

**Files.** `packages/ml/src/cocok_ml/datagen/t3_ingest.py`, `data/manifests/own_hand.parquet`, annotations JSON.

**Specs.** FS-DG-10.  **Docs.** `docs/progress/CP-09.md` (counts per style/doc_type/condition; time spent per doc).

**Gate** (`cp09.sh`): 100 T3 items in manifest · split counts exactly 30/70 and stratified (table printed) · every item has GT JSON + `total_amount` bbox · no EXIF in any stored image · 10 random image↔scenario pairs listed for a **manual spot check** (Arka confirms in the log).

**Done when.** Spot check 10/10 correct; style labels recorded.

**Debug playbook.**
| Symptom | Likely cause | Check / fix |
|---|---|---|
| Photo matched to the wrong scenario | Batch renaming by order | Rename per photo right after writing; spot-check before ingest |
| Many blurry photos | Low light / motion | Re-shoot; keep blur as a *condition*, not an accident (label it) |
| Wrote a value different from the sheet | Human error | Correct the GT JSON to what is **written** (the image is the truth), log it |

---

## CP-10 — Dataset v0.1 assembly

| A | W3 Wed–Thu | 1.5 d | Owner: A:R2 + H✓ (publish) | Depends: CP-08 (CP-09 appended when done) | Tag: `cp-10` |
|---|---|---|---|---|---|

**Goal.** Versioned splits and tiers (T0–T3, calib) exist with a dataset card and a license-guarded publish path.

**Tasks.**
1. [A:R2] Build splits per blueprint §4.4: synth train (≈ 20 000 docs, configurable), synth val/calib ≥ 1 500, T0 test ≈ 1 000; T2 calib ≥ 300 / T2 test ≈ 500; T1 from official test splits; T3 slots reserved and filled by CP-09 via the same tool.
2. [A:R2] `cocok-data publish --dry-run` with publish guard (FS-DG-09): refuses ND and non-publishable items; writes dataset card sections automatically (counts, licenses).
3. [A:R8] `docs/DATASET_CARD.md` (sources, licenses, tiers, splits, limitations, fictional-data statement, known limitation of T3).
4. [H✓] Approve the private HF push (`cocok-docs-v0.1`), public only after license review.

**Files.** `packages/ml/src/cocok_ml/datagen/{splits.py,publish.py}`, `data/manifests/dataset_v0.1.parquet`, `docs/DATASET_CARD.md`.

**Specs.** FS-DG-08, FS-DG-09.  **Docs.** Dataset card; `docs/progress/CP-10.md`.

**Gate** (`cp10.sh`): leakage check across **all** split pairs (sha256 + source_item_id) · counts match config ± 0 · publish dry-run refuses a planted `orand_car` item (asserted) · dataset card has all required headings · `datasets.load_dataset(<private repo>)` round trip on 10 items (SLOW).

**Done when.** One command rebuilds the dataset from raw data + config with identical manifest hashes.

**Debug playbook.**
| Symptom | Likely cause | Check / fix |
|---|---|---|
| Leakage via composites | Same CVL crop reused in calib and test composites | Track `source_item_id` lists per composite; split crops **before** compositing |
| HF upload stalls | Many small files | Shard into parquet/webdataset tars; `upload_large_folder` |
| T3 counts wrong after append | Re-split on append | Splits are assigned once at ingest and stored; never recomputed |

---

## CP-11 — Eval harness v1 + metrics  `[metrics LEARNING-CRITICAL]`

| A | W3 Fri → W4 Mon | 2 d | Owner: A:R2 (runner/replay/report) + H+T (metrics) | Depends: CP-10 | Tag: `cp-11` |
|---|---|---|---|---|---|

**Goal.** One command turns any route's predictions into per-tier metrics with confidence intervals, plots, and a replayable cache.

**Tasks.**
1. [A:R2] Prediction record format (JSONL, one line per item): `item_id, route, run_id, fields{value_raw, value_normalized, confidence, bbox, bbox_source, signals}, raw_output, cost_usd, latency_ms, peak_rss_mb, error`.
2. [A:R2] `cocok-eval run` (FS-EH-01), `cocok-eval replay` (FS-EH-02), report writer with CI columns + plots (FS-EH-03).
3. [A:R6] Failing tests for FS-EV-01…08 (hand-computed toy fixtures; Clopper–Pearson table incl. `(k=0,n=299) → UCB ≤ 0.01` and `(k=0,n=298) → UCB > 0.01`).
4. [H] Implement metric functions FS-EV-01…08.
5. [A:R2] Sanity routes: `oracle` (GT as prediction, confidence 1.0) and `random`.

**Files.** `packages/ml/src/cocok_ml/eval/{runner.py,replay.py,report.py,cli.py}`, `packages/ml/src/cocok_ml/eval/metrics/*.py` [H], `evals/configs/*.yaml`.

**Specs.** FS-EV-01 … FS-EV-08, FS-EH-01 … FS-EH-03.  **Docs.** `docs/progress/CP-11.md`.

**Gate** (`cp11.sh`): `pytest -m cp11` · oracle route → every accuracy = 1.0 with CI upper = 1.0 · random route accuracy near chance · `replay` reproduces `metrics.json` byte-identically from cache · report lints: every metric row has a CI.

**Done when.** Arka can compute ECE for a 10-item toy example by hand and it matches the function.

**Debug playbook.**
| Symptom | Likely cause | Check / fix |
|---|---|---|
| Risk–coverage curve jagged / order-dependent | Ties in confidence | Sort by confidence desc, group ties, evaluate at group boundaries only |
| ECE NaN | Empty bins | Weight each bin by its count; skip empty bins |
| Replay differs from run | Normalization code changed between run and replay | Store `code_sha` + `rules_version` per run; replay recomputes with current code by design — diff explains it |

---

## CP-12 — Baselines B4 (digital) + B1a/B1b (OCR-VLM)

| A | W4 Tue–Wed | 1.5 d | Owner: A:R2 | Depends: CP-11 | Tag: `cp-12` |
|---|---|---|---|---|---|

**Goal.** Measured accuracy, cost, latency and memory for the digital routes and the two OCR-specialist routes.

**Tasks.**
1. [A:R2] `prompts/structure_text_v1.md` (front matter `id`, `version`, `model_family`); structured output with the exported JSON schema.
2. [A:R2] B4a `pypdfium2` layout text → LLM; B4b Docling 2.x → LLM. Record `peak_rss_mb` (ADR-0010).
3. [A:R2] B1a PaddleOCR-VL-1.6 → text LLM; B1b GLM-OCR KIE prompt → JSON. Run on Kaggle GPU via a notebook that installs `cocok-ml` at a pinned commit and calls the CLI.
4. [A:R2] Log every run to MLflow; store raw outputs in the replay cache.

**Files.** `prompts/*.md`, `packages/ml/src/cocok_ml/baselines/*.py`, `notebooks/kaggle/b1_ocr_vlm.ipynb`.

**Specs.** FS-AD-01 (prototype), FS-AD-03 (prototype), FS-EH-01.  **Docs.** `docs/progress/CP-12.md` (table: route × tier × accuracy/CI × cost × latency × RSS).

**Gate** (`cp12.sh`): metrics.json exists for B1a, B1b, B4a, B4b on applicable tiers · every run has MLflow id, prompt version, model revision · replay cache present · invalid-JSON rate reported.

**Done when.** ADR-0010 has numbers to decide with.

**Debug playbook.**
| Symptom | Likely cause | Check / fix |
|---|---|---|
| PaddleOCR-VL dependency conflicts | Mixing paddle + torch in one env | Separate Kaggle notebook/env per model; pin from the model card |
| GPU OOM on Kaggle | Large page images | Resize to the model's recommended max pixels; batch size 1 |
| LLM returns prose, not JSON | No structured-output mode / schema too large | Use provider JSON-schema mode; count failures as wrong; retry once |

---

## CP-13 — Baselines B2 + B3, EVAL_REPORT v0.1 → **Milestone A gate**

| A | W4 Thu–Fri | 2 d | Owner: A:R2 + H (report, post) | Depends: CP-12, CP-09 | Tags: `cp-13`, `milestone-a`, `cocok-docs-v0.1` |
|---|---|---|---|---|---|

**Goal.** All baselines compared on all tiers with honest intervals, and the first public write-up.

**Tasks.**
1. [A:R2] B2: 2–3 API VLMs (exact model ids + date); Kaggle Community Benchmarks run if D4 = yes (SDK supports images).
2. [A:R2] B3: `Qwen/Qwen3.5-2B` zero-shot, non-thinking, fp16 on Kaggle T4, pinned revision; transformers v5.
3. [A:R2] Provider data-policy guard: eval config maps tier → allowed providers; runner **refuses** to send T3/`orand_car` images to free-tier providers (FS-EH-01 rule) — tested.
4. [A:R8 + H] `docs/EVAL_REPORT.md` v0.1: per-tier tables with CIs, cost/latency/RSS, error-analysis section (10 failure examples with images), Docling decision (ADR-0010 follow-up).
5. [H] LinkedIn post 1 (benchmark findings; link to report; no claims beyond the report).

**Files.** `packages/ml/src/cocok_ml/baselines/*`, `notebooks/kaggle/b3_qwen35.ipynb`, `docs/EVAL_REPORT.md`.

**Specs.** FS-AD-02 (prototype), FS-EH-01…03.  **Docs.** EVAL_REPORT v0.1, `docs/progress/CP-13.md`.

**Gate** (`cp13.sh`): `make eval-report` rebuilds the report from cache with no network · every baseline row has per-tier metrics + CI + cost + latency · data-policy guard test passes · `gates-upto CP=13`.

**Done when (Milestone A).** Every baseline has per-tier metrics, cost and latency; the report is reproducible from one command.

**Debug playbook.**
| Symptom | Likely cause | Check / fix |
|---|---|---|
| 429 / rate limits | Free-tier quotas | `tenacity` exponential backoff + jitter; resume from cache (runner skips done items) |
| Qwen3.5 load error | transformers < 5 | Pin `transformers>=5,<6`; restart kernel after install |
| Slow first Qwen step on T4 | Triton kernel compilation | Expected; time it separately; don't count it in latency |
| Costs higher than expected | Large images → many tokens | Downscale to the model's recommended resolution; record tokens per doc |

---

# Milestone B — Models + calibration (W5–W7: 2026-11-02 → 11-20)

## CP-14 — CRNN amount reader from scratch  `[LEARNING-CRITICAL]`

| B | W5 Mon–Tue | 2 d | Owner: H+T (model, loss use, decode, loop); A:R2 (data loaders, ONNX export) | Depends: CP-13 | Tag: `cp-14` |
|---|---|---|---|---|---|

**Goal.** Arka's own CRNN+CTC reads handwritten rupiah amounts from crops, runs on CPU, and is reported on T1 with CIs.

**Tasks.**
1. [A:R2] Crop datasets and loaders: `names` train (pretraining, letters charset), synthetic amount crops from CP-07/08 renders, `cvl_hds` train; height-normalized to 32 px, variable width, padded per batch with true widths kept.
2. [A:R6] Failing tests: `CharsetCodec` round trip (FS-CR-01), shape tests (B×1×32×W → T×B×C) (FS-CR-02), CTC decode on hand-made logits (FS-CR-03), "overfit 64 samples" test (SLOW) (FS-CR-04).
3. [H] Implement `CharsetCodec` (FS-CR-01), `CRNN` (FS-CR-02), `ctc_greedy_decode` (FS-CR-03), `train_one_epoch`/`evaluate` (FS-CR-04). Pretrain on names, swap the classifier head to the amount charset, fine-tune.
4. [A:R2] ONNX export with dynamic width + parity test (FS-CR-05); CPU latency benchmark (p50/p95 per crop, 1 thread).
5. [A:R2] MLflow logging (curves, config, data manifest hash).

**Files.** `packages/ml/src/cocok_ml/train/crnn/{codec.py,model.py,decode.py,train.py}` [A — learning-critical, study guide required], `packages/ml/src/cocok_ml/train/export_onnx.py` [A — shared by CRNN and TrOCR].

**Specs.** FS-CR-01 … FS-CR-05.  **Docs.** `docs/MODEL_CARD.md` (CRNN section), `docs/progress/CP-14.md`.

**Gate** (`cp14.sh`): `pytest -m cp14` · overfit test reaches 100 % exact match on 64 samples (SLOW) · ONNX parity max|Δlogit| < 1e-3 on 100 crops · T1 exact match reported with 95 % CI · CPU p95 latency logged.

**Done when.** Arka can draw the tensor shapes from image to CTC loss on a whiteboard.

**Debug playbook.**
| Symptom | Likely cause | Check / fix |
|---|---|---|
| CTC loss = inf / NaN | Output length T too short for label (needs T ≥ L + repeats) | Reduce horizontal pooling; `zero_infinity=True` only as a diagnostic, not a fix |
| Predicts only blanks for long | Normal early; or LR too high/low | Wait ~1 epoch; then LR range test |
| Wrong loss dimension | `log_softmax` on batch dim; tensors not (T, N, C) | Assert shapes; `F.log_softmax(x, dim=2)` before `CTCLoss` |
| Blank index clash | Blank = 0 but charset also uses 0 | Charset indices start at 1; blank reserved at 0 |
| ONNX parity fails | Dropout/BatchNorm in train mode during export | `model.eval()` before export; opset ≥ 17 |

---

## CP-15 — TrOCR fine-tune + amount-reader decision

| B | W5 Wed–Thu | 1.5 d | Owner: A:R2; H✓ decision | Depends: CP-14 | Tag: `cp-15` |
|---|---|---|---|---|---|

**Goal.** A fair from-scratch vs pretrained comparison decides which amount reader ships.

**Tasks.**
1. [A:R2] Fine-tune `microsoft/trocr-small-handwritten` on the same amount data (same splits, same eval).
2. [A:R2] Export the winner-candidate(s) to ONNX (encoder–decoder) and benchmark CPU latency + RSS.
3. [A:R2] Comparison table: T1 exact match (CI), CPU p50/p95, model size, training GPU-hours and cost.
4. [H✓] ADR-0015 "Amount reader choice" (winner by T1 exact match; latency must fit the 2 GB host).

**Files.** `packages/ml/src/cocok_ml/train/trocr/*`, `docs/adr/0015-amount-reader-choice.md`.

**Specs.** FS-CR-05 (export reused).  **Docs.** MODEL_CARD (TrOCR section), ADR-0015, `docs/progress/CP-15.md`.

**Gate** (`cp15.sh`): both arms evaluated with identical item lists (asserted by manifest hash) · comparison table present · selected model artifact on HF with revision recorded · ADR-0015 merged.

**Debug playbook.**
| Symptom | Likely cause | Check / fix |
|---|---|---|
| TrOCR outputs letters for digits | Tokenizer/vocab not constrained | Constrained decoding or post-filter to the charset; report both |
| ONNX decoder export fails | Past-key-values / dynamic axes | Use Hugging Face Optimum export for VisionEncoderDecoder; pin versions |
| CPU latency too high | Beam search | Greedy decoding; quantize to int8 (dynamic) and re-check accuracy |

---

## CP-16 — Grounding by OCR alignment

| B | W5 Fri | 1 d | Owner: A:R2/R3 | Depends: CP-13 | Tag: `cp-16` |
|---|---|---|---|---|---|

**Goal.** Every extracted value gets a trustworthy box (or an explicit "none"), independent of the extractor (ADR-0006).

**Tasks.**
1. [A:R3] `RapidOcrEngine` adapter (FS-AD-04): models baked into the image/package (no runtime download); returns lines with quad → normalized axis-aligned boxes, text, score.
2. [A:R3] `ground_value` (FS-AD-07): normalized fuzzy match + layout anchors (`Jumlah`, `Total`, `Rp`, `Terbilang`), returns `(bbox, bbox_source, s_ocr_agree)`.
3. [A:R2] Report: IoU vs GT boxes on T0/T2 for `total_amount` (and all fields), latency p95, RSS; amount reader accuracy with GT crops vs aligned crops.

**Files.** `packages/adapters/src/cocok_adapters/{ocr/rapidocr.py,grounding/align.py}`, tests with 10 golden fixtures.

**Specs.** FS-AD-04, FS-AD-07.  **Docs.** `docs/progress/CP-16.md`.

**Gate** (`cp16.sh`): golden fixtures pass · `ground_value` returns `bbox=None, source="none"` when no line exceeds the similarity threshold (test) · IoU report produced · RSS of OCR process logged.

**Debug playbook.**
| Symptom | Likely cause | Check / fix |
|---|---|---|
| Boxes in wrong place | Quad points not normalized by image size | Normalize by (w, h) of the image **actually** passed to OCR (after resize) |
| `1.250.000` never matches OCR `1250000` | Comparing raw strings | Compare normalized values (FS-CV-01) and digit-only strings |
| First call very slow | Model download/initialization at runtime | Ship models in the package; init once per worker |

---

## CP-17 — VLM LoRA fine-tune (Qwen3.5-2B)

| B | W6 Mon–Wed | 2.5 d | Owner: A:R2 (Arka monitors runs) | Depends: CP-13 | Tag: `cp-17` |
|---|---|---|---|---|---|

**Goal.** A 16-bit LoRA adapter on Qwen3.5-2B that emits schema-valid JSON, trained reproducibly on free GPUs.

**Tasks.**
1. [A:R2] SFT dataset: (image, instruction) → canonical JSON (schema key order, integers for money, `null` for missing); only from train splits; leakage-checked.
2. [A:R2] Kaggle notebook pinned (Unsloth, TRL, transformers v5, peft); vision layers frozen; loss on assistant tokens only; fp16 on T4; checkpoint every N steps to `/kaggle/working` for resume.
3. [A:R2] **Smoke run** 50 steps → check finite, decreasing loss; then the full run.
4. [A:R2] Push adapter to HF (private until model card ready); MLflow run; record GPU-hours.

**Files.** `packages/ml/src/cocok_ml/train/vlm_lora/{dataset.py,train.py,infer.py}`, `notebooks/kaggle/vlm_lora_qwen35.ipynb`.

**Specs.** (agent-owned; see FUNCTION_SPECS §6 notes).  **Docs.** MODEL_CARD (VLM section draft), `docs/progress/CP-17.md` (loss curves, GPU-hours).

**Gate** (`cp17.sh`): smoke-run log shows finite loss and `loss[50] < loss[1]` · adapter loads and produces schema-valid JSON on ≥ 95 % of 20 val docs · label-masking test (decoded labels contain only the assistant JSON).

**Debug playbook.**
| Symptom | Likely cause | Check / fix |
|---|---|---|
| Loss NaN in fp16 | Overflow; LR too high | LR 2e-4 → 5e-5, grad clip 1.0, check loss scaling; fallback Modal L4 (bf16) |
| OOM on T4 | Image token count too high | Lower max image pixels; batch 1 + grad accumulation; gradient checkpointing |
| Model learns to repeat the prompt | Loss on prompt tokens | Verify `labels == -100` for every non-assistant token |
| Session dies at 12 h | Kaggle limit | Resume from last checkpoint; plan runs < 9 h |
| Slow start on T4 | Qwen3.5 Triton kernel compile | Expected; do not kill the run |

---

## CP-18 — Confidence signals + calibrator  `[LEARNING-CRITICAL]`

| B | W6 Wed–Fri | 2 d | Owner: H+T (signals, apply, fit); A:R2 (plumbing) | Depends: CP-15, CP-16 | Tag: `cp-18` |
|---|---|---|---|---|---|

**Goal.** Per-field signals become a calibrated P(correct) that means what it says on each tier.

**Tasks.**
1. [A:R6] Failing tests FS-CF-01, FS-CF-02, FS-CF-04 (missing-signal encoding, monotonicity of isotonic, JSON round trip, parity sklearn-fit vs core-apply |Δ| < 1e-9).
2. [H] `build_signal_vector` (core), `apply_calibrator` (core, pure), `fit_calibrator` (ml, scikit-learn) with 5-fold CV model selection (logistic vs isotonic) by log-loss.
3. [A:R2] Wire: eval predictions → signal vectors → calibrator → updated confidences in the replay cache; reliability diagrams per tier.

**Files.** `packages/core/src/cocok_core/confidence/{signals.py,calibrator.py}` [H], `packages/ml/src/cocok_ml/calibrate/fit.py` [H], `rules/calibrator.json`.

**Specs.** FS-CF-01, FS-CF-02, FS-CF-04.  **Docs.** `docs/progress/CP-18.md` (ECE before/after with CIs, per tier).

**Gate** (`cp18.sh`): `pytest -m cp18` · parity test · calibrator JSON schema-valid and versioned · ECE (with CI) reported for raw vs calibrated on calib (CV) and on each test tier.

**Debug playbook.**
| Symptom | Likely cause | Check / fix |
|---|---|---|
| Logistic weights explode | Perfectly separating signal | L2 regularization (tune `C` in CV) |
| Calibrated on calib, badly off on T3 | Distribution shift (synthetic → real) | This is a finding: report it; `T3-calib` exists to measure it |
| You "balanced" classes and ECE got worse | Re-weighting changes base rate | Never rebalance for calibration; keep natural frequencies |

---

## CP-19 — SGR abstention policy, risk–coverage, ablation  `[LEARNING-CRITICAL policy]`

| B | W7 Mon–Tue | 1.5 d | Owner: H+T (FS-CF-03, FS-CF-05); A:R2 (ablation runner) | Depends: CP-18 | Tag: `cp-19` |
|---|---|---|---|---|---|

**Goal.** τ is selected with a finite-sample guarantee, and we know how much each signal contributes.

**Tasks.**
1. [A:R6] Failing tests: SGR on synthetic Bernoulli data with known risk — over 1 000 simulations the true risk of the selected τ exceeds the target in ≤ 5 % of runs (SLOW); edge cases (no feasible τ → coverage 0).
2. [H] `select_threshold_sgr` (ml/calibrate) and `decide_document` (core) per FS-CF-05 / FS-CF-03.
3. [A:R2] Write τ to `rules/confidence.yaml` with `version`, `calib_manifest_sha256`, `ucb`, `delta`, `target`.
4. [A:R2] Ablation runner: drop one signal at a time (+ "GT bbox vs aligned bbox"), refit calibrator, re-select τ, report Δ certified automation rate with CI.

**Files.** `packages/ml/src/cocok_ml/calibrate/sgr.py` [H], `packages/core/src/cocok_core/confidence/policy.py` [H], `packages/ml/src/cocok_ml/eval/ablation.py` [A], `rules/confidence.yaml`.

**Specs.** FS-CF-03, FS-CF-05, FS-EV-04 … FS-EV-06.  **Docs.** `docs/progress/CP-19.md`.

**Gate** (`cp19.sh`): `pytest -m cp19` (simulation test SLOW) · `rules/confidence.yaml` validates and its `calib_manifest_sha256` matches the current calib manifest · risk–coverage plots (empirical + certified point) per tier exist · ablation table has a CI per row.

**Debug playbook.**
| Symptom | Likely cause | Check / fix |
|---|---|---|
| Certified coverage = 0 | Too few auto-approved calib docs, or a weak signal set | Check n (≈ 530 accepted docs with 0 errors under SGR's Bonferroni split); enlarge calib via generator; report honestly |
| Simulation test fails | Bonferroni over search steps missing; off-by-one in UCB | Re-read FS-CF-05 algorithm; check δ / ⌈log₂ m⌉ |
| τ differs every run | Non-deterministic calibrator CV folds | Seed the CV splitter |

---

## CP-20 — Adoption decisions + EVAL_REPORT v0.2 → **Milestone B gate**

| B | W7 Wed (+ Thu–Fri slack) | 1 d | Owner: H✓ + A:R2/R8 | Depends: CP-17, CP-19 | Tags: `cp-20`, `milestone-b` |
|---|---|---|---|---|---|

**Goal.** Evidence-based decisions on which models ship, published as a reproducible report.

**Tasks.**
1. [A:R2] Full pipeline eval (extract → ground → amount reader → validators → calibrator → SGR) for: best zero-shot API route, fine-tuned Qwen3.5-2B, Docling vs pypdfium2 digital route.
2. [H✓] ADR-0016 "Primary visual extractor" (adoption rule §5.3, certified metric) and ADR-0017 "Digital route" (ADR-0010 follow-up).
3. [A:R8] EVAL_REPORT v0.2 (risk–coverage, reliability, ECE, ablation, cost/latency, certified vs empirical); MODEL_CARD complete; publish adapter/model on HF.
4. [H] Use slack days for anything red; otherwise start CP-24 early.

**Files.** `docs/EVAL_REPORT.md`, `docs/MODEL_CARD.md`, `docs/adr/0016-*.md`, `docs/adr/0017-*.md`.

**Gate** (`cp20.sh`): `make eval-report` reproduces v0.2 from cache · ADRs merged · `gates-upto CP=20` (FULL=1 once).

**Done when (Milestone B).** Risk–coverage curve and ablation reproducible; adoption decisions recorded as ADRs.

---

# Milestone C — Product (W8–W11: 2026-11-23 → 12-18)

Tracks inside C (max two agent tracks at once): **Backend** CP-21 → 22 → 23 → 25 · **Human** CP-24 (parallel to 21–22) ·
**Web** CP-26 → 27 → 28 (starts on the OpenAPI draft + mock) · **Ops** CP-29 → 30 → 31.

## CP-21 — Database schema, migrations, repositories

| C | W8 Mon–Tue | 2 d | Owner: A:R3 | Depends: CP-20 | Tag: `cp-21` |
|---|---|---|---|---|---|

**Goal.** PostgreSQL 18 schema for §6.4 with reversible migrations, least-privilege roles and tested repositories.

**Tasks.**
1. [A:R3] `infra/compose/compose.dev.yml`: `postgres:18` (+ `pg_trgm`); MinIO for S3-compatible dev storage.
2. [A:R3] Alembic migrations for every §6.4 table incl. `sessions`, `audit_log`, `worker_heartbeats`; schemas `app`, `queue`, `lg`; PK default `uuidv7()`.
3. [A:R3] Roles: `cocok_migrator` (DDL), `cocok_app` (DML; **no UPDATE/DELETE on `audit_log`**), `cocok_readonly`.
4. [A:R3] SQLAlchemy 2 async models + repositories (FS-AD-08) with psycopg 3; `IdGenerator` (uuid-utils) + `Clock` adapters (FS-AD-10).

**Files.** `migrations/*`, `packages/adapters/src/cocok_adapters/db/*`, `infra/compose/compose.dev.yml`, tests.

**Specs.** FS-AD-08, FS-AD-10.  **Docs.** `docs/ARCHITECTURE.md` (data model section, ER diagram), `docs/progress/CP-21.md`.

**Gate** (`cp21.sh`): migrations upgrade → downgrade → upgrade on empty PG18 (testcontainers) · `cocok_app` UPDATE on `audit_log` raises permission error (test) · repository contract tests (`-m "cp21 and integration"`) · UUIDv7 ids sort by creation time (test).

**Debug playbook.**
| Symptom | Likely cause | Check / fix |
|---|---|---|
| testcontainers can't reach Docker on macOS | Socket path differs (OrbStack/Desktop) | `export DOCKER_HOST=unix://$HOME/.orbstack/run/docker.sock` (or Desktop path); `TESTCONTAINERS_RYUK_DISABLED=true` only if needed |
| "attached to a different loop" in async tests | Engine created in another event loop | One loop per session (pytest-asyncio `loop_scope="session"`), engine fixture in the same scope |
| Downgrade fails | Enum types/extensions not dropped | Every `op.create_*` has a matching `op.drop_*` in reverse order |

---

## CP-22 — Adapters + contract tests

| C | W8 Wed–Thu | 2 d | Owner: A:R3 | Depends: CP-21 | Tag: `cp-22` |
|---|---|---|---|---|---|

**Goal.** Every port has production adapters that pass one shared contract suite, with timeouts and cost recording.

**Tasks.**
1. [A:R3] `Storage`: local + S3 (presigned GET, short TTL) (FS-AD-06); contract suite runs against both (MinIO in tests).
2. [A:R3] `LLMClient` for the chosen providers with provider-native structured output, timeouts, retries on retryable errors, cost per call (FS-AD-01); recorded-response fixtures.
3. [A:R3] `VisualExtractor` and `DigitalExtractor` (FS-AD-02, FS-AD-03) wrapping LLMClient + prompts; `OnnxAmountReader` (FS-AD-05); `RapidOcrEngine` from CP-16.
4. [A:R3] `JobQueue` (Procrastinate) with `enqueue_in_tx` (FS-AD-09).

**Files.** `packages/adapters/src/cocok_adapters/{storage,llm,ocr,amount_reader,queue}/*`, `packages/adapters/tests/contracts/*`.

**Specs.** FS-AD-01 … FS-AD-06, FS-AD-09.  **Docs.** `docs/progress/CP-22.md`.

**Gate** (`cp22.sh`): contract suites green for every adapter · timeout test (fake slow server → `ExternalTimeout` within budget) · every LLM call returns `cost_usd` and `prompt_version` · `PAID_MODELS_ENABLED=false` makes paid adapters raise before any network call.

**Debug playbook.**
| Symptom | Likely cause | Check / fix |
|---|---|---|
| Presigned URL 403 in browser | Clock skew or wrong region/endpoint | Use the bucket's region; sync time; test with `curl` |
| Recorded fixtures go stale | Provider response shape changed | Re-record with a script, review diff in PR |
| ONNX session slow per call | Session created per request | Create once per process; set `intra_op_num_threads` |

---

## CP-23 — Worker pipeline (Procrastinate + LangGraph)

| C | W9 Mon–Wed | 2.5 d | Owner: A:R3 | Depends: CP-22 | Tag: `cp-23` |
|---|---|---|---|---|---|

**Goal.** Uploaded documents flow through the typed node graph to `AUTO_APPROVED`/`NEEDS_REVIEW`, idempotently and crash-safely.

**Tasks.**
1. [A:R3] `tasks.py`: `process_document(document_id)` Procrastinate task; queueing lock = `sha256:pipeline_version`; retry strategy for `RetryableError` only.
2. [A:R3] `graph.py` + `nodes/*` per blueprint §6.1 (FS-WK-01 … FS-WK-05); thread id `{document_id}:{pipeline_version}`; Postgres checkpointer in schema `lg`.
3. [A:R3] `persist` writes extraction run, fields, match result and FSM transition **in one transaction**; `emit_events` writes audit entries.
4. [A:R3] Heartbeat loop; `FAILED` with `reason` after max retries.

**Files.** `apps/worker/src/cocok_worker/*`, tests.

**Specs.** FS-WK-01 … FS-WK-05, FS-AD-09.  **Docs.** `docs/ARCHITECTURE.md` (pipeline + FSM diagrams), `docs/progress/CP-23.md`.

**Gate** (`cp23.sh`): 10 fixture docs (recorded LLM) end in the expected status · **crash-resume test**: kill after `extract` checkpoint → restart → LLM fixture call count stays 1 (ADR-0005) · **duplicate enqueue test**: two enqueues of the same doc → one job (ADR-0004) · **rollback test**: enqueue inside a rolled-back tx → zero jobs · `! grep -rn "interrupt(" apps/worker` · failure path: 3 retryable errors → `FAILED` with reason.

**Debug playbook.**
| Symptom | Likely cause | Check / fix |
|---|---|---|
| Job runs twice | Lock key not deterministic | Key from `sha256 + pipeline_version` only; no timestamps |
| Resume repeats the LLM call | Node not idempotent / side effect before checkpoint | Pure node outputs; side effects only in `persist`/`emit_events` |
| Status stuck in `PROCESSING` | Exception swallowed in a node | Every node raises typed errors; worker maps them to FSM events; log with `document_id` |
| Checkpoint tables grow | No pruning | Prune threads of terminal documents after 7 days (periodic task) |

---

## CP-24 — PO matching incl. three-way match  `[LEARNING-CRITICAL]`

| C | W8 Mon–Tue (parallel to CP-21/22) | 1.5 d | Owner: H+T | Depends: CP-04 | Tag: `cp-24` |
|---|---|---|---|---|---|

**Goal.** Documents are matched to POs line by line with explainable discrepancies, measured on planted perturbations.

**Tasks.**
1. [A:R6] Failing tests FS-MT-01 … FS-MT-06 + golden cases (exact match; qty over/under; price mismatch; unmatched lines; duplicate doc number; synonyms "sak/zak", "btg/batang").
2. [H] Implement matching functions.
3. [A:R2] Discrepancy detection P/R on T0 planted perturbations (blueprint §2 `discrepancy_detection`) via replay.

**Files.** `packages/core/src/cocok_core/matching/*` [H], tests.

**Specs.** FS-MT-01 … FS-MT-06.  **Docs.** `docs/progress/CP-24.md` (P/R table with CIs).

**Gate** (`cp24.sh`): `pytest -m cp24` · golden cases · P/R report produced (no target; honest number).

**Debug playbook.**
| Symptom | Likely cause | Check / fix |
|---|---|---|
| Lines matched to the wrong PO line | Greedy matching on similarity only | Optimal assignment on a cost matrix (similarity + qty/price closeness) |
| "Semen Gresik 40kg" ≠ "SEMEN GRESIK 40 KG" | Normalization | Lowercase, strip punctuation, unit synonyms, number–unit spacing |
| Duplicate detector flags legit re-issues | Key too coarse | Key = (vendor key, normalized doc_number, doc_date year) |

---

## CP-25 — API: auth/sessions/CSRF/RBAC, documents, review

| C | W9 Wed–Fri | 2.5 d | Owner: A:R3 (+ A:R7 review) | Depends: CP-23, CP-24 | Tag: `cp-25` |
|---|---|---|---|---|---|

**Goal.** A secure, contract-first REST API (blueprint §6.3) that drives the FSM and the worker.

**Tasks.**
1. [A:R3] Auth per ADR-0008: `pwdlib` argon2id, sessions table, cookie attributes, CSRF double-submit + Origin check, RBAC guards (FS-AP-05 … FS-AP-07); rate limits on auth/upload.
2. [A:R3] Upload (FS-AP-01): magic-byte allowlist, size/page/pixel limits, re-encode images, storage key = UUID, `Idempotency-Key`, transactional enqueue.
3. [A:R3] Review use cases (FS-AP-02 … FS-AP-04): correct field (reason required; audit), approve/reject via FSM, review queue with cursor pagination.
4. [A:R3] problem+json mapping (FS-AP-08), `/healthz`, `/readyz` (FS-AP-09); security headers middleware.
5. [A:R3] OpenAPI export → `apps/web/src/api/schema.d.ts` generated in CI; Schemathesis job.

**Files.** `apps/api/src/cocok_api/*`, tests, `openapi.json`.

**Specs.** FS-AP-01 … FS-AP-09.  **Docs.** `docs/SECURITY.md` (auth section), `docs/progress/CP-25.md`.

**Gate** (`cp25.sh`): API tests (`-m cp25`) · auth tests from ADR-0008 (cookie flags, logout revokes, role change revokes, CSRF missing → 403, session id rotates on login) · upload attack tests (polyglot, oversize, decompression bomb, wrong magic bytes) → 4xx problem+json · Schemathesis: no 5xx · OpenAPI diff reviewed (`git diff --exit-code openapi.json` after regeneration).

**Debug playbook.**
| Symptom | Likely cause | Check / fix |
|---|---|---|
| Browser doesn't send the cookie | Cross-site setup or `Secure` on http | Same-site domains (ADR-0008); local dev over `https://localhost` via Caddy or relax `Secure` only in `local` env |
| CORS error with credentials | `allow_origins=["*"]` with credentials | Exact origin allowlist + `allow_credentials=True` |
| Schemathesis finds 500 | Unhandled validation path | Map to problem+json; add the case as a regression test |

---

## CP-26 — Web foundation: login, upload, queue

| C | W8 Thu → W9 | 2 d | Owner: A:R4 | Depends: CP-25 (OpenAPI draft is enough to start) | Tag: `cp-26` |
|---|---|---|---|---|---|

**Goal.** A Next.js 16 app with auth, upload and review queue on the generated client.

**Tasks.**
1. [A:R4] Scaffold Next.js 16 (TypeScript strict, Tailwind v4, shadcn/ui, TanStack Query v5, Zod v4, openapi-fetch); ESLint flat config via CLI; Vitest; Playwright.
2. [A:R4] `proxy.ts` auth redirect; login/logout; CSRF header on mutations.
3. [A:R4] `/upload` (multi-file, per-file progress, `Idempotency-Key` per file — FS-WB-03); `/queue` (filters, sort by lowest confidence, cursor pagination).
4. [A:R4] Mock server (Prism from `openapi.json`) for development before the API is live.

**Files.** `apps/web/*`, `.github/workflows/ci-web.yml`.

**Specs.** FS-WB-03.  **Docs.** `apps/web/README.md`, `docs/progress/CP-26.md`.

**Gate** (`cp26.sh`): `make web-check` (typecheck, lint, vitest, build) · Playwright smoke: login → upload 2 files → both appear in queue (local stack).

**Debug playbook.**
| Symptom | Likely cause | Check / fix |
|---|---|---|
| `cookies()` type errors | Next 16 async dynamic APIs | `await cookies()` everywhere; run the Next codemod |
| `middleware.ts` ignored | Renamed in Next 16 | Use `proxy.ts` exporting `proxy` |
| Generated types out of date | Client not regenerated | CI step regenerates and fails on diff |

---

## CP-27 — Review page with grounding + Playwright critical path

| C | W10 Mon–Wed | 2.5 d | Owner: A:R4 | Depends: CP-26 | Tag: `cp-27` |
|---|---|---|---|---|---|

**Goal.** A reviewer can verify, correct and approve a document quickly with visual evidence.

**Tasks.**
1. [A:R4] Viewer (image + PDF via pdf.js) with zoom/pan; bbox overlays from normalized coordinates (FS-WB-01), colored by `bbox_source`.
2. [A:R4] Field panel: value, confidence badge, signal evidence ("amount reader disagrees", "terbilang mismatch"), inline correction with reason; approve/reject (manager role only).
3. [A:R4] Keyboard shortcuts (FS-WB-02): next field, accept, edit, approve, reject, next document.
4. [A:R6] Playwright critical path upload → review → correct → approve; axe-core accessibility scan.

**Files.** `apps/web/src/app/documents/[id]/*`, `apps/web/src/components/review/*`, `apps/web/e2e/*`.

**Specs.** FS-WB-01, FS-WB-02.  **Docs.** `docs/progress/CP-27.md` (GIF of the flow).

**Gate** (`cp27.sh`): `make e2e` (critical path green) · bbox transform unit tests (zoom/rotation/page offsets) · axe: no serious/critical violations · staff role cannot see the approve button and gets 403 from the API if forced.

**Debug playbook.**
| Symptom | Likely cause | Check / fix |
|---|---|---|
| Overlays misaligned after zoom | Using CSS pixels of the container, not rendered image size | Compute from the rendered image's bounding rect; one tested helper |
| PDF overlay off on page 2 | Page offset not added | bbox has `page`; add cumulative page offsets |
| Flaky Playwright test | Waiting on timeouts | Wait on network idle / specific `data-testid` states |

---

## CP-28 — Purchase orders, dashboard, about

| C | W10 Thu–Fri | 1.5 d | Owner: A:R4 (+ A:R6 tests) | Depends: CP-27 | Tag: `cp-28` |
|---|---|---|---|---|---|

**Goal.** PO matching results and product metrics are visible; the method and limitations are explained.

**Tasks.** [A:R4] `/purchase-orders` list/detail with match status + discrepancies · `/dashboard` (automation, abstain, correction hotspots, cost/doc, p95 latency, queue depth) from `GET /metrics/summary` · `/about` (method, limitations, links to EVAL_REPORT/dataset/models) · loading/empty/error states for every view.

**Files.** `apps/web/src/app/{purchase-orders,dashboard,about}/*`.

**Gate** (`cp28.sh`): component tests for the three states per page · dashboard numbers equal a SQL fixture computed in an API test · `make web-check`.

---

## CP-29 — Observability

| C | W9 Thu → W10 | 1.5 d | Owner: A:R5 | Depends: CP-23 | Tag: `cp-29` |
|---|---|---|---|---|---|

**Goal.** Every request and pipeline run is traceable end-to-end, logs are safe, and failures alert someone.

**Tasks.** [A:R5] OpenTelemetry for FastAPI + worker nodes; Langfuse SDK v4 (OTel-native) for LLM calls with prompt id/version, model, tokens, cost; structlog JSON with `request_id/job_id/document_id` + redaction processor (NPWP/NIK → last 4); Sentry (optional); scheduled uptime workflow; daily-spend and failure-rate checks; container memory alert.

**Files.** `packages/adapters/src/cocok_adapters/observability/*`, `apps/*/…/telemetry.py`, `.github/workflows/uptime.yml`.

**Gate** (`cp29.sh`): one processed fixture doc yields a trace with all node spans and the LLM generation linked (test exporter) · redaction test (no full NPWP/NIK/secret in captured logs) · uptime workflow dry-run passes.

**Debug playbook.**
| Symptom | Likely cause | Check / fix |
|---|---|---|
| LLM spans not under the request trace | Context not propagated into worker | Store `traceparent` with the job; restore it in the task |
| Duplicate spans | Both auto-instrumentation and manual | Pick one per library |

---

## CP-30 — Containers, EC2, OIDC, deploy + automatic rollback

| C | W10 Mon–Wed | 2.5 d | Owner: A:R5 (H✓ for AWS console steps) | Depends: CP-25, CP-29 | Tag: `cp-30` |
|---|---|---|---|---|---|

**Goal.** `main` deploys itself to a 2 GB Graviton box and rolls back automatically when unhealthy.

**Tasks.**
1. [A:R5] Multi-stage, non-root Dockerfiles (api, worker: **no torch**, RapidOCR + ONNX models baked in); `compose.prod.yml` with memory limits per §15; 1 GB swap.
2. [A:R5] Build on native amd64 + arm64 runners; merge manifest; push to ECR (OIDC role, least privilege).
3. [H✓] EC2 `t4g.small` (SSM agent, no SSH port), Elastic IP, security group 80/443 only; Caddy with `api.<domain>`; SSM parameters for secrets.
4. [A:R5] `deploy.sh` (backup → pull → migrate → up → readiness → rollback on failure), `rollback.sh <sha>`; `deploy.yml` via SSM Run Command.
5. [A:R5] Vercel project on `app.<domain>`; preview deployments point to the demo API.

**Files.** `infra/docker/*`, `infra/compose/compose.prod.yml`, `infra/caddy/Caddyfile`, `infra/scripts/{deploy,rollback}.sh`, `.github/workflows/deploy.yml`, `docs/RUNBOOK.md`.

**Specs.** FS-OP-01, FS-OP-02.  **Docs.** RUNBOOK (deploy, rollback), `docs/progress/CP-30.md`.

**Gate** (`cp30.sh`): image manifest lists `linux/amd64` and `linux/arm64` · **rollback drill**: deploy an image whose `/readyz` fails → previous SHA is running again within the time budget (logged) · prod memory: total RSS < 1.6 GB idle, 10-document smoke run without OOM · security headers present (`curl -sI`) · TLS valid.

**Debug playbook.**
| Symptom | Likely cause | Check / fix |
|---|---|---|
| OIDC `AssumeRoleWithWebIdentity` denied | Trust policy `sub` doesn't match repo/branch | Match `repo:<owner>/cocok:ref:refs/heads/main` exactly |
| Worker OOM-killed | Models loaded per job / torch in image | One model load per process; check `docker stats`; image must not contain torch |
| Caddy can't get a certificate | DNS not pointing to the Elastic IP / port 80 blocked | `dig api.<domain>`; open 80 for ACME HTTP-01 |

---

## CP-31 — Backups + restore drill, security review, eval-gate CI

| C | W11 Mon–Tue | 1.5 d | Owner: A:R5 (backups), A:R7 (security), A:R6 (eval gate) | Depends: CP-30 | Tag: `cp-31` |
|---|---|---|---|---|---|

**Goal.** Data survives disasters, the security baseline is verified, and model/prompt changes cannot silently regress quality.

**Tasks.**
1. [A:R5] `backup.sh` (pg_dump -Fc → age → S3 with lifecycle; weekly off-cloud copy) and `restore.sh` (FS-OP-03, FS-OP-04); nightly schedule.
2. [A:R5 + H] **Restore drill**: restore last backup into a scratch DB, run smoke tests, record RPO/RTO in RUNBOOK.
3. [A:R7] STRIDE-lite threat model for C; §13 checklist walk-through with evidence links.
4. [A:R6] `eval-gate.yml`: replay gate + live gate per blueprint §11; demo PR with a deliberately harmful rule change must fail.

**Files.** `infra/scripts/{backup,restore}.sh`, `.github/workflows/eval-gate.yml`, `evals/gate.yaml`, `docs/RUNBOOK.md`, `docs/SECURITY.md`.

**Specs.** FS-OP-03, FS-OP-04, FS-EH-04.  **Docs.** RUNBOOK (backup/restore + drill log), SECURITY (threat model), `docs/progress/CP-31.md`.

**Gate** (`cp31.sh`): drill log entry exists with measured RTO ≤ 2 h · backup object is encrypted (cannot be read without the age key) · §13 checklist has no unchecked item without an issue link · eval-gate demo PR failed as expected (link in log).

---

## CP-32 — Vendor memory (SHOULD) → **Milestone C gate**

| C | W11 Wed–Thu | 1.5 d | Owner: A:R3 | Depends: CP-31 | Tags: `cp-32`, `milestone-c` |
|---|---|---|---|---|---|

**Goal.** Human corrections make the next document from the same vendor better — measured, not assumed.

**Tasks.** [A:R3] Store corrections keyed by vendor NPWP → name (`pg_trgm` fuzzy second) (FS-VM-01); use as few-shot examples for the API route; auto-create regression cases. [A:R2] Before/after on a repeat-vendor subset with CIs.

**Gate** (`cp32.sh`): lookup order test (NPWP exact → trigram → none; no embeddings) · before/after metric reported with CI · `gates-upto CP=32` (FULL=1).

**Done when (Milestone C).** Live demo; Playwright critical path green; restore drill logged; security checklist §13 complete.

*(If behind schedule: cut CP-32 per the cut line and move it to the backlog; the C gate then runs at CP-31.)*

---

# Launch — W12 (2026-12-21 → 12-25)

## CP-33 — Docs, video, release v1.0.0 (+ buffer)

| L | W12 | 1.5 d (+ buffer) | Owner: H + A:R8 | Depends: CP-32 | Tags: `cp-33`, `v1.0.0` |
|---|---|---|---|---|---|

**Goal.** A recruiter understands Cocok in 10 seconds and an engineer in 10 minutes.

**Tasks.** [A:R8] README final (headline metric with CI + risk–coverage chart, live link, architecture image, quickstart, limitations); ARCHITECTURE, RUNBOOK, EVAL_REPORT, DATASET_CARD, MODEL_CARD, SECURITY, FAILURE_LOG, HOW_I_USED_AI current. [H] 90-second demo video; LinkedIn post 2; edit HOW_I_USED_AI. [A:R1] CHANGELOG, release v1.0.0; dataset/model made public after license review (H✓).

**Gate** (`cp33.sh`): every §17 file exists and has no `TODO` · link check (`lychee docs README.md`) · live `/readyz` 200 · `gates-upto CP=33` (FULL=1).

**Done when.** You can send one link to a recruiter without explaining anything else.
