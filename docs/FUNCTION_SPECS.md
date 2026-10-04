# COCOK — Function Specifications

```yaml
doc_id: cocok-function-specs
version: 1.0.0
blueprint_version: 2.1.0
status: proposed
```

This file documents **every significant function or piece of logic** in Cocok: what it must do, what it must
never do, worked examples that become tests, edge cases, and who writes it. It is written *before* the code.

> **Since ADR-0014 every entry is implemented by the AI.** Entries marked `[LEARNING-CRITICAL]` (formerly
> "human-owned") additionally get a study guide in `docs/learning/`, and Arka studies and tests them before
> sign-off. Examples in each entry become acceptance tests first.

---

## 0. How to use this file

### 0.1 What counts as "significant"

A function gets an FS entry if **any** of these is true: it encodes a business rule (money, tax, matching,
abstention); it computes a reported metric; it crosses a trust boundary (uploads, auth, model output, external
APIs); it changes persistent state (DB writes, FSM transitions, jobs); or a bug in it would silently produce a
wrong number. Glue code, DTOs and trivial getters do not get entries — their docstrings are enough.

### 0.2 Entry format

Each entry has: **ID · signature · owner · checkpoint · module**, then *Purpose*, *Contract* (pre/postconditions,
invariants, purity), *Examples* (table → become tests), *Errors*, *Edge cases*, *Approach notes* (hints for
the reasoning a reader needs to understand the implementation), *Tests* (what R6 writes), *Used by*.

### 0.3 Docstring standard (Google style, enforced by `ruff` `D` rules)

The first docstring line ends with the FS-ID in parentheses followed by a period — `… rupiah (FS-CV-01).` —
so `grep FS-CV-01` finds the spec, the code and the tests (pydocstyle D415 requires the final period).
`Examples:` in `packages/core` are executed by `pytest --doctest-modules`.

```python
def parse_money(text: str) -> Money:
    """Parse Indonesian rupiah text into integer rupiah (FS-CV-01).

    Accepts `Rp`/`IDR` prefixes, dot thousands separators, trailing `,-`/`,00`,
    and `rb`/`jt` suffixes. Never guesses OCR character confusions.

    Args:
        text: Raw text as extracted, e.g. ``"Rp 1.250.000,-"``.

    Returns:
        Money with ``amount_idr`` as an exact integer.

    Raises:
        MoneyParseError: With a machine-readable ``code`` (see FS-CV-01).

    Examples:
        >>> parse_money("Rp 1.250.000,-").amount_idr
        1250000
        >>> parse_money("500rb").amount_idr
        500000

    Notes:
        Why no O→0 substitution: a normalizer that "fixes" OCR errors hides them
        from the confidence model; disagreement must stay visible.
    """
```

### 0.4 Global conventions

* **Money** is `Money(amount_idr: int)`. Never `float`. Quantities are `Decimal`.
* **Bboxes** are `[page, x0, y0, x1, y1]`, page 0-based, coordinates normalized to [0, 1], **top-left origin**.
* **Errors** derive from `cocok_core.errors.DomainError` and carry a stable `code: str` (UPPER_SNAKE). Callers
  branch on `code`, never on message text.
* **Purity:** everything in `packages/core` is pure — no I/O, no clock, no randomness (time via `Clock`, ids via
  `IdGenerator`, randomness via an explicit `numpy.random.Generator` only in `ml`).
* **Determinism:** same inputs → same outputs, including ordering of returned lists (sort explicitly).

---

## 1. Core domain models (`packages/core/src/cocok_core/models`, `errors.py`, `ports`) — agent-owned (R3), CP-02

### FS-CM-01 `Money`
`@dataclass(frozen=True, slots=True, order=True) class Money: amount_idr: int` — *implemented CP-02*
* **Contract.** Immutable; `amount_idr` must be exactly `int` (`bool`, `float`, `Decimal`, `str` → `TypeError`;
  stricter than v2.1, which allowed integral `Decimal`). **Negative amounts are allowed** (differences such as
  `invoice − PO`); "a total must be positive" is a validator rule (CP-04). Supports `+`, `-`, unary `-`,
  comparison and `sum(xs, Money.zero())` (no `0 + Money`). Multiplication only via
  `Money.times(qty: Decimal, rounding)` with `rounding ∈ {"half_up","half_even","floor","ceiling"}`; NaN/∞ and
  `float` qty rejected; computed at 60-digit precision, then rounded once.
* **Inside Pydantic models** `amount_idr` is `Strict()`: `1250000.0`, `"1250000"`, `true` and extra keys are
  rejected. ⚠ `model_validate(..., strict=False)` overrides this — never pass it.
* **Examples.** `Money(1_250_000) + Money(50_000) == Money(1_300_000)`; `Money(1.5)` → `TypeError`;
  `Money(10_000).times(Decimal("2.5"), "half_up") == Money(25_000)`.
* **Tests.** Hypothesis: associativity and commutativity of `+`, `(a + b) - b == a`, `times(Decimal(1)) == self`;
  table of rounding modes incl. negative amounts; huge amounts stay exact.

### FS-CM-02 `DocumentStatus`, `Event`, `transition` — *implemented CP-02*
`def transition(current: DocumentStatus, event: Event, *, retry_count: int = 0) -> DocumentStatus`
* **Contract.** Implements blueprint §6.2 exactly as a read-only lookup table; pure; raises
  `InvalidTransition(code="INVALID_TRANSITION", current=..., event=...)` for any pair not in the table.
  `FAILED → QUEUED` only via `Event.RETRY` and only if `retry_count < MAX_RETRIES (3)`, else
  `InvalidTransition(code="RETRY_LIMIT_REACHED")`. Negative `retry_count` → `ValueError` (caller bug).
  Helpers: `allowed_events(status) -> frozenset[Event]`, `TERMINAL = {REJECTED, POSTED}`.
* **Transition table (the test oracle).**

| From | Event | To |
|---|---|---|
| UPLOADED | ENQUEUE | QUEUED |
| QUEUED | START | PROCESSING |
| PROCESSING | EXTRACTED | EXTRACTED |
| PROCESSING | FAIL | FAILED |
| EXTRACTED | AUTO_APPROVE | AUTO_APPROVED |
| EXTRACTED | NEED_REVIEW | NEEDS_REVIEW |
| NEEDS_REVIEW | APPROVE | APPROVED |
| NEEDS_REVIEW | REJECT | REJECTED |
| AUTO_APPROVED, APPROVED | POST | POSTED |
| FAILED | RETRY (retry_count < 3) | QUEUED |

* **Tests.** Exhaustive parametrization over all 10 × 10 `DocumentStatus × Event` pairs against a hand-copied
  oracle; every status reachable from UPLOADED; every non-terminal status can reach a terminal one; Hypothesis
  `RuleBasedStateMachine` with random event sequences.

### FS-CM-03 `ExtractedDocument`, `LineItem`, `FieldMeta`, `REQUIRED_FIELDS` — *implemented CP-02*
* **Contract.** Pydantic v2 models mirroring blueprint §3.2, `ConfigDict(frozen=True, extra="forbid")`.
  **Every field except `doc_type` is optional (`None`)**: requiredness lives only in `REQUIRED_FIELDS`
  (and `REQUIRED_LINE_ITEM_FIELDS`: surat jalan items need `description` + `qty`), so a missing field becomes a
  `MISSING_REQUIRED` issue (FS-CV-08) instead of a crash.
* **Field types.** Free text: blank → `None`, 1–500 chars. `vendor_npwp` exactly 16 digits, `vendor_nitku` exactly
  22 digits (normalization happens in FS-CV-04/05). `doc_date`: strict `date` (ISO string in JSON; timestamps and
  `"01/10/2026"` rejected — D/M/Y parsing is FS-CV-03). `qty`: `Decimal`, serialized as a JSON **string**
  (`"2.5"`), schema `type: string, pattern ^-?\d+(\.\d+)?$`; `"2,5"`, `"1e3"`, NaN rejected.
  `line_items`: tuple, `null` → `()`.
* **`FieldMeta`.** `value_raw`, `value_normalized` (JSON value), `confidence ∈ [0, 1] | None` (None = not yet
  calibrated), `bbox = (page ≥ 0, x0, y0, x1, y1)` with `0 ≤ x0 < x1 ≤ 1`, `0 ≤ y0 < y1 ≤ 1`, `bbox_source`,
  `signals: dict[str, float]`. Invariant: a box needs a source, and source `none` needs no box.
* **Where metadata lives (decision CP-02).** NOT inside `ExtractedDocument` — that schema is the LLM output format
  and must not ask the model to invent confidences. Metadata travels in `ExtractionResult.field_meta`, keyed by
  field path: `"total_amount"` or `"line_items[0].unit_price"` (`is_valid_field_path`).
* **Schema export.** `python -m cocok_core.schema_export --write|--check PATH`; sorted keys, 2-space indent, short
  descriptions only (docstrings must not leak into the LLM schema); golden snapshot
  `schemas/extracted_document.schema.json`.
* **Edge cases.** `qty` accepts `"2,5"`? **No** — models receive normalized values; parsing lives in FS-CV-*.

### FS-CM-04 Error hierarchy — *implemented CP-02*
`DomainError(message: str = "", *, code: str | None = None, **context)` → `DomainValidationError`
(`MoneyParseError`, `DateParseError`, `NpwpError`, `TerbilangError`, `RulesError`), `InvalidTransition`,
`InvalidModelOutput` (FS-AD-01), `LicenseViolation`, `CalibratorMismatch`, `RetryableError` (`ExternalTimeout`,
`RateLimited`, `ProviderUnavailable`), `PermanentExternalError`.
* **Contract.** Every class has a unique UPPER_SNAKE `default_code`; a raise may override `code`; invalid codes →
  `ValueError`. `context` is read-only; `to_dict()` gives `{code, message, context}` for the API. `RetryableError`
  is the **only** base the queue retries on. Names without an `Error` suffix are deliberate (ruff N818 ignored
  for `errors.py` only).
* **Rename (CP-02).** v2.1 called the validation base `ValidationError`; it is `DomainValidationError` now, because
  `pydantic.ValidationError` is used in the same modules and identical names in one `except` hide bugs.

### FS-CM-05 Ports (`typing.Protocol`) — *implemented CP-02 in `cocok_core.ports`*
Signatures (async where I/O). Images cross ports as `PageImage` (encoded bytes + mime + size + page) because
`core` may not import numpy; adapters decode. DB transactions cross as the opaque `Transaction` protocol, so `core`
never imports psycopg. All ports are `@runtime_checkable`.
```python
class Extractor(Protocol):
    async def extract(self, doc: DocumentInput) -> ExtractionResult: ...

    # DocumentInput(document_id, pages: tuple[PageImage, ...], doc_type_hint, page_texts)
    # ExtractionResult(document, field_meta: Mapping[path, FieldMeta], extractor_id, raw_output,
    #                  cost_usd: Decimal, latency_ms)


class AmountReader(Protocol):
    def read(self, crop: PageImage) -> AmountRead: ...  # text, value: Money|None, seq_prob


class OcrEngine(Protocol):
    def lines(self, page: PageImage) -> list[OcrLine]: ...  # text, box (normalized), score


class Storage(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> None: ...
    async def get(self, key: str) -> bytes: ...
    async def presign_get(self, key: str, ttl_s: int) -> str: ...


class LLMClient(Protocol):
    async def structured(self, req: StructuredRequest) -> StructuredResponse: ...

    # StructuredRequest(prompt_id, system, user, json_schema, schema_name, images, max_output_tokens)
    # StructuredResponse(data, raw_text, model_id, input_tokens, output_tokens, cost_usd, latency_ms)


class JobQueue(Protocol):
    async def enqueue_in_tx(
        self, tx: Transaction, task: str, args: Mapping[str, object], lock: str
    ) -> str | None: ...  # job id, or None if a job with this lock is already queued


class Clock(Protocol):
    def now(self) -> datetime: ...  # tz-aware UTC


class IdGenerator(Protocol):
    def new(self) -> UUID: ...  # UUIDv7
```
* **Contract.** Ports expose domain types only (no SDK objects) — enforced by `test_ports_speak_domain_types_only`.
  Each port has one shared contract-test suite (`packages/adapters/tests/contracts/test_<port>.py`) parametrized
  over adapters. Test fakes for every port live in `packages/core/tests/test_ports.py`.
* **Repository ports** (database access) are defined in CP-21/22 together with the schema (decision CP-02: their
  shape depends on the tables, so guessing them now would only create rework).

---

## 2. Validation (`packages/core/src/cocok_core/validation`) — `[LEARNING-CRITICAL]` — CP-03, CP-04

### FS-CV-01 `parse_money` / `parse_money_detailed`  `[LEARNING-CRITICAL]` · CP-03 · `validation/money.py`
```python
def parse_money(text: str) -> Money: ...
def parse_money_detailed(
    text: str,
) -> MoneyParse: ...  # MoneyParse(money, variant: Literal["id","en","plain","spaced","suffix"], had_currency: bool)
```
**Purpose.** Turn any common Indonesian way of writing an amount into exact integer rupiah.

**Contract.** Pure. Case-insensitive. Leading/trailing whitespace ignored. Accepts an optional currency token
(`Rp`, `Rp.`, `IDR`) before the number, optional sign `-` before or after the currency token, and the trailing
markers `,-`, `.-`, `,00`, `,—`. Never substitutes characters (no `O→0`, `l→1`). Result range |amount| < 10¹⁵.

**Examples (→ tests).**

| Input | Output | variant |
|---|---|---|
| `"Rp 1.250.000,-"` | 1 250 000 | id |
| `"Rp1.250.000"` | 1 250 000 | id |
| `"Rp. 1.250.000,00"` | 1 250 000 | id |
| `"Rp 1.250.000.-"` | 1 250 000 | id |
| `"IDR 500.000"` | 500 000 | id |
| `"1250000"` | 1 250 000 | plain |
| `"1 250 000"` | 1 250 000 | spaced |
| `"1.250"` | 1 250 | id |
| `"1,250,000"` | 1 250 000 | en |
| `"500rb"` / `"500 ribu"` / `"500k"` | 500 000 | suffix |
| `"1,25 jt"` / `"1,25jt"` / `"1.25 juta"` | 1 250 000 | suffix |
| `"0,5 rb"` | 500 | suffix |
| `"-Rp 50.000"` | −50 000 | id |
| `"Rp 1.250.000,50"` | `MoneyParseError(NONZERO_DECIMALS)` | |
| `"1.25"` | `MoneyParseError(BAD_GROUPING)` | |
| `"1.2500.000"` | `MoneyParseError(BAD_GROUPING)` | |
| `"1.500 rb"` | `MoneyParseError(AMBIGUOUS_SEPARATOR)` (1,5 rb or 1.500 rb?) | |
| `"1,2345 jt"` | `MoneyParseError(BAD_GROUPING)` | |
| `""`, `"   "` | `MoneyParseError(EMPTY)` | |
| `"Rp"` | `MoneyParseError(NO_DIGITS)` | |
| `"12a00"` | `MoneyParseError(UNEXPECTED_CHAR)` | |
| `"1.250,000"` | `MoneyParseError(AMBIGUOUS_SEPARATOR)` | |

**Errors.** `MoneyParseError.code ∈ {EMPTY, NO_DIGITS, UNEXPECTED_CHAR, BAD_GROUPING, AMBIGUOUS_SEPARATOR,
NONZERO_DECIMALS, OUT_OF_RANGE}`.

**Approach notes (hints).**
* Peel layers in a fixed order: trim → lowercase → sign/currency token → trailing markers → suffix unit
  (`rb|ribu|k` = 10³, `jt|juta` = 10⁶). Each layer is a tiny, separately testable step.
* Without a suffix: decide the role of `.` and `,` from **pattern**, not position: a separator followed by
  exactly three digits, repeated consistently from the left group of 1–3 digits, is a thousands separator.
  A single comma followed by 1–2 digits at the end is a decimal part (must be zeros).
* With a suffix: at most one separator (`,` or `.`). Followed by 1–2 digits → decimal part (compute with
  `Decimal`; the result is always an integer because the multiplier is ≥ 10³). Followed by exactly 3 digits →
  `AMBIGUOUS_SEPARATOR` ("1.500 rb" could be 1,5 rb or 1 500 rb). 4+ digits → `BAD_GROUPING`.
* Mixed separators that don't fit a known pattern → `AMBIGUOUS_SEPARATOR` (refusing is a valid answer here;
  the document goes to review).

**Tests.** Table above; Hypothesis: `parse_money(format_money(m, style)) == m` for every style and
`|m| < 10¹⁵`; `parse_money` never returns for strings containing letters other than the allowed tokens.

**Used by.** FS-CV-08, FS-CV-10, FS-AD-07 (grounding comparison), generator round-trip checks.

---

### FS-CV-02 `format_money`  `[LEARNING-CRITICAL]` · CP-03 · `validation/money.py`
`def format_money(m: Money, style: Literal["plain", "kwitansi", "compact"] = "plain") -> str`

| m | plain | kwitansi | compact |
|---|---|---|---|
| 1 250 000 | `Rp 1.250.000` | `Rp 1.250.000,-` | `Rp1.250.000` |
| 0 | `Rp 0` | `Rp 0,-` | `Rp0` |
| −50 000 | `-Rp 50.000` | `-Rp 50.000,-` | `-Rp50.000` |

**Contract.** Pure; dot thousands separators; no decimals. **Tests.** Table + round-trip with FS-CV-01.

---

### FS-CV-03 `parse_date_id` / `parse_date_id_detailed`  `[LEARNING-CRITICAL]` · CP-03 · `validation/dates.py`
```python
def parse_date_id(text: str, *, ref: date) -> date: ...
def parse_date_id_detailed(
    text: str, *, ref: date
) -> DateParse: ...  # DateParse(value, had_place_prefix, weekday_mismatch: bool|None, format: str)
```
**Purpose.** Indonesian dates in any common written form → `datetime.date`.

**Contract.** Pure (`ref` is passed in; never call `date.today()`). Day–month–year order **only** (plus ISO
`YYYY-MM-DD`). Strips a leading place prefix (`"Jombang, 1 Oktober 2026"`) and weekday prefix (`Senin`, `Selasa`,
`Rabu`, `Kamis`, `Jumat`/`Jum'at`, `Sabtu`, `Minggu`/`Ahad`). Two-digit years → `2000+yy` if that is ≤ `ref.year + 1`,
else `1900+yy`.

**Month vocabulary.** Januari/Jan · Februari/Pebruari/Feb/Peb · Maret/Mar · April/Apr · Mei · Juni/Jun ·
Juli/Jul · Agustus/Agu/Agt/Ags/Aug · September/Sept/Sep · Oktober/Okt/Oct · November/Nopember/Nov/Nop ·
Desember/Des/Dec · Roman numerals I–XII (`"1-X-2026"`).

**Examples.**

| Input (ref = 2026-10-01) | Output |
|---|---|
| `"1 Oktober 2026"` | 2026-10-01 |
| `"01 Okt 2026"` | 2026-10-01 |
| `"Jombang, 1 Oktober 2026"` | 2026-10-01 (had_place_prefix) |
| `"Kamis, 1 Oktober 2026"` | 2026-10-01 (weekday ok) |
| `"Senin, 1 Oktober 2026"` | 2026-10-01 (weekday_mismatch = True) |
| `"01/10/2026"`, `"1-10-2026"`, `"1.10.2026"` | 2026-10-01 |
| `"01/10/26"` | 2026-10-01 |
| `"5/10/26"` | 2026-10-05 (never May 10) |
| `"1-X-2026"` | 2026-10-01 |
| `"2026-10-01"` | 2026-10-01 |
| `"12 Nopember 2025"` | 2025-11-12 |
| `"31/02/2026"` | `DateParseError(INVALID_DATE)` |
| `"Oktober 2026"` | `DateParseError(MISSING_DAY)` |
| `""` | `DateParseError(EMPTY)` |

**Errors.** `{EMPTY, UNKNOWN_FORMAT, UNKNOWN_MONTH, MISSING_DAY, INVALID_DATE}`.
**Approach notes.** Normalize (lowercase, unify separators `/ - .` and multiple spaces) → strip prefixes → try a
small ordered list of patterns; validate with `date(y, m, d)` inside `try`. Keep the month table as data.
**Tests.** Table; Hypothesis: for random valid dates and each output format the generator uses,
`parse_date_id(render(d)) == d`.

---

### FS-CV-04 `normalize_npwp` (+ `mask_tax_id`)  `[LEARNING-CRITICAL]` · CP-03 · `validation/npwp.py`
```python
def normalize_npwp(
    text: str,
) -> Npwp: ...  # Npwp(value: str  # 16 digits, source_format: Literal["legacy15","npwp16","nik16"])
def mask_tax_id(value: str) -> str: ...  # "************1000" — used by log redaction
```
**Purpose.** Canonical 16-digit taxpayer id from any written form.

**Contract.** Pure; idempotent (`normalize_npwp(n.value) == n`). Strip a leading label (`NPWP`, `NPWP:`, `NIK`,
`No. NPWP`), then the separators space `.` `-` `/`. Any other non-digit (e.g. letter `O`) → `NON_DIGIT_CONTENT`;
blank input → `EMPTY`. Length 15 → `"0" + digits`, `source_format="legacy15"`. Length 16 starting
with `0` → `npwp16`. Length 16 not starting with `0` → `nik16` (personal NPWP = NIK). **Structural only** — no
checksum (none is officially published for our purposes).

**Examples.**

| Input | value | source_format |
|---|---|---|
| `"01.234.567.8-901.000"` | `0012345678901000` | legacy15 |
| `"012345678901000"` | `0012345678901000` | legacy15 |
| `"0012 3456 7890 1000"` | `0012345678901000` | npwp16 |
| `"NPWP: 0012.3456.7890.1000"` | `0012345678901000` | npwp16 |
| `"3578012345670001"` | `3578012345670001` | nik16 |
| `"0012345678901000000000"` (22) | `NpwpError(LOOKS_LIKE_NITKU)` | |
| `"1234"` | `NpwpError(BAD_LENGTH)` | |
| `"0000000000000000"` | `NpwpError(ALL_ZEROS)` | |
| `"01.234.567.8-9O1.000"` (letter O) | `NpwpError(NON_DIGIT_CONTENT)` | |

**Tests.** Table; Hypothesis idempotence; masking never reveals more than the last 4 digits.

### FS-CV-05 `normalize_nitku`  `[LEARNING-CRITICAL]` · CP-03 · `validation/npwp.py`
`def normalize_nitku(text: str) -> Nitku`  — `Nitku(value: str  # 22 digits, npwp: Npwp, place_code: str, is_head_office: bool)`
* **Contract.** Strip non-digits; exactly 22 digits; first 16 must pass `normalize_npwp`; last 6 = place code;
  `"000000"` → head office. 21 digits (legacy + 6) → `NpwpError(BAD_LENGTH)` — do not guess a conversion.
* **Examples.** `"0012345678901000000000"` → head office; `"0012345678901000000001"` → branch `000001`.

---

### FS-CV-06 `to_terbilang`  `[LEARNING-CRITICAL]` · CP-04 · `validation/terbilang.py`
`def to_terbilang(n: int, *, suffix_rupiah: bool = False) -> str`
**Purpose.** Canonical Indonesian words for an integer (lowercase, single spaces). Decoration (Title Case, `#…#`,
"Rupiah") is the generator's job.

**Contract.** `0 ≤ n < 10¹⁵` else `ValueError`. Scales: ribu (10³), juta (10⁶), miliar (10⁹), triliun (10¹²).
`se-` forms: *sepuluh, sebelas, seratus, seribu*; **never** *sejuta/semiliar* in canonical output.

**Examples (golden set seed; R6 extends to ≥ 200).**

| n | words |
|---|---|
| 0 | nol |
| 1 | satu |
| 10 | sepuluh |
| 11 | sebelas |
| 12 | dua belas |
| 19 | sembilan belas |
| 20 | dua puluh |
| 21 | dua puluh satu |
| 100 | seratus |
| 101 | seratus satu |
| 110 | seratus sepuluh |
| 111 | seratus sebelas |
| 999 | sembilan ratus sembilan puluh sembilan |
| 1 000 | seribu |
| 1 001 | seribu satu |
| 1 100 | seribu seratus |
| 2 000 | dua ribu |
| 11 000 | sebelas ribu |
| 100 000 | seratus ribu |
| 101 000 | seratus satu ribu |
| 111 111 | seratus sebelas ribu seratus sebelas |
| 1 000 000 | satu juta |
| 1 001 000 | satu juta seribu |
| 1 250 000 | satu juta dua ratus lima puluh ribu |
| 2 000 000 000 | dua miliar |
| 1 000 000 000 000 | satu triliun |

**Approach notes.** One function converts a 0–999 group (hundreds → "seratus"/"X ratus"; tens with the *belas*
special case; units). The scale loop walks groups from the largest scale down, skipping zero groups. The only
scale with a *se-* rule is *ribu* when the group equals 1.

### FS-CV-07 `parse_terbilang` / `parse_terbilang_detailed`  `[LEARNING-CRITICAL]` · CP-04 · `validation/terbilang.py`
```python
def parse_terbilang(text: str) -> int: ...
def parse_terbilang_detailed(
    text: str,
) -> (
    TerbilangParse
): ...  # value, canonical: bool, variants_used: list[str], noise_removed: list[str]
```
**Purpose.** Read terbilang as people actually write it on kwitansi.

**Contract.** Pure, lenient on form, strict on meaning. Removes noise tokens/characters: `# = * ( ) : . , -`,
`terbilang`, `rupiah`, `rp`, `saja`. Accepts glued words (`duapuluh`, `limaratus`, `seratusribu`), *se-* forms
including `sejuta`, spelling variants `milyar`, `trilyun`, and non-canonical `satu ribu`, `satu ratus`.
Rejects tokens it does not know and scale words out of order.

**Examples.**

| Input | Output |
|---|---|
| `"# Satu Juta Dua Ratus Lima Puluh Ribu Rupiah #"` | 1 250 000 |
| `"satu juta duaratus limapuluh ribu rupiah"` | 1 250 000 |
| `"sejuta rupiah"` | 1 000 000 (canonical = False) |
| `"satu ribu lima ratus"` | 1 500 (variant "satu ribu") |
| `"dua milyar"` | 2 000 000 000 (variant "milyar") |
| `"Terbilang: sebelas ribu rupiah saja"` | 11 000 |
| `"seratus satu ribu"` | 101 000 |
| `"sepuluh ribu seratus"` | 10 100 |
| `"satu ribu satu juta"` | `TerbilangError(BAD_ORDER)` |
| `"dua puluh lima kilo"` | `TerbilangError(UNKNOWN_TOKEN, token="kilo")` |
| `"rupiah"` | `TerbilangError(NOT_A_NUMBER)` |
| `""` | `TerbilangError(EMPTY)` |

**Errors.** `{EMPTY, UNKNOWN_TOKEN, BAD_ORDER, NOT_A_NUMBER, OUT_OF_RANGE}`.

**Approach notes (hints).**
* Two stages: (1) **segmentation** — turn the cleaned string into known morphemes by longest-match against a
  small vocabulary (units, `belas`, `puluh`, `ratus`, scale words, `se`); (2) **evaluation** — a left-to-right
  accumulator with a *current group* (< 1000) and a *total*; scale words close the group.
* `belas`, `puluh`, `ratus` modify the immediately preceding unit (or `se` = 1).
* Enforce that each scale word is smaller than the previous one (that is the `BAD_ORDER` check).

**Tests.** Table; Hypothesis: `parse_terbilang(to_terbilang(n)) == n` for `0 ≤ n < 10¹⁵`; decorated variants
from the generator (Title Case, `#`, glued) round-trip too.

---

### FS-CV-08 `check_arithmetic`  `[LEARNING-CRITICAL]` · CP-04 · `validation/arithmetic.py`
```python
def check_arithmetic(doc: ExtractedDocument, *, tol: Tolerances, tax: TaxRules, ref: date) -> list[Issue]
# Issue(code: str, field_path: str, expected: int | None, actual: int | None, severity: Literal["blocking","warning"])
```
**Purpose.** Find internal inconsistencies in an extracted document — the cheapest, strongest error signal.

**Contract.** Pure; **never raises for data problems** (only for programming errors); returns issues sorted by
`(field_path, code)`. Skips a check when an input it needs is missing (and the missing field is reported by
`MISSING_REQUIRED` only if it is required for that doc_type).

| Code | Rule | Severity |
|---|---|---|
| `LINE_TOTAL_MISMATCH` | `|qty × unit_price − line_total| > tol.line_abs_idr` (qty × price rounded per `tol.rounding`) | blocking |
| `SUBTOTAL_MISMATCH` | `|Σ line_total − subtotal| > tol.subtotal_abs_idr` (only if all line totals present) | blocking |
| `TOTAL_MISMATCH` | `|subtotal + (tax or 0) − total| > tol.total_abs_idr` | blocking |
| `TAX_MISMATCH` | `tax_amount` present and differs from `compute_ppn(subtotal)` by > `tol.tax_abs_idr` | warning |
| `TERBILANG_MISMATCH` | `parse_terbilang(amount_in_words) != total_amount` | blocking |
| `TERBILANG_UNPARSEABLE` | `amount_in_words` present but parse fails | warning |
| `MISSING_REQUIRED` | a field in `REQUIRED_FIELDS[doc_type]` is null/empty | blocking |
| `NEGATIVE_AMOUNT` | subtotal/tax/total < 0 | blocking |
| `FUTURE_DATE` | `doc_date > ref + tol.future_days` | warning |

**Examples.** Lines (2 sak × 65 000 = 130 000), (3 batang × 85 000 = 255 000); subtotal 385 000; tax null;
total 385 000; words "tiga ratus delapan puluh lima ribu rupiah" → `[]`. Change total to 358 000 →
`[TERBILANG_MISMATCH, TOTAL_MISMATCH]` (sorted by field_path).

**Tests.** Table-driven; Hypothesis: a consistent generated scenario yields `[]`; any single planted perturbation
from FS-DG-02 yields exactly its expected code.

### FS-CV-09 `compute_ppn` + `TaxRules` loader  · CP-04
`def compute_ppn(base_idr: int, *, on: date, category: Literal["non_luxury","luxury"], rules: TaxRules) -> PpnResult`
— `PpnResult(dpp: int, rate: Decimal, ppn: int, rule_id: str)` — computation `[LEARNING-CRITICAL]`; YAML schema/loader
agent-owned (R3).

**Rule file (`rules/tax.yaml`) — fields per rule:** `id, category, effective_from, effective_to|null, rate,
dpp_numerator, dpp_denominator, rounding_dpp, rounding_ppn, legal_basis, source_url, accessed`.
State to encode (verify on pajak.go.id when writing — blueprint §5.5): from 2025-01-01, PMK 131/2024:
`non_luxury` rate 0.12 with DPP = 11/12 × price (effective 11 %); `luxury` rate 0.12 with DPP = price.

**Contract.** Exactly one rule must match `(category, on)`; zero → `RulesError(NO_RULE)`, more →
`RulesError(OVERLAPPING_RULES)`. All math in `Decimal`; rounding modes from the rule (`half_up` | `floor`).

**Examples** (non_luxury):

| base | rounding half_up: dpp / ppn | rounding floor: dpp / ppn |
|---|---|---|
| 1 000 000 | 916 667 / 110 000 | 916 666 / 109 999 |
| 1 250 000 | 1 145 833 / 137 500 | 1 145 833 / 137 499 |
| 999 | 916 / 110 | 915 / 109 |

(The table shows why rounding mode must be data: different modes give different rupiah.)

### FS-CV-10 `normalize_field` / `fields_equal`  `[LEARNING-CRITICAL]` · CP-04 · `validation/fields.py`
```python
def normalize_field(field: str, value_raw: str, *, doc_type: DocType, ref: date) -> NormalizedValue
def fields_equal(field: str, a: NormalizedValue, b: NormalizedValue) -> bool
```
**Purpose.** The **single** definition of "same value" used by validators, the eval harness (blueprint §11: same
normalization for every route) and the calibrator labels.

| Field | Normalization |
|---|---|
| subtotal, tax_amount, total_amount, unit_price, line_total | FS-CV-01 → int |
| doc_date | FS-CV-03 → ISO date |
| vendor_npwp | FS-CV-04 → 16 digits |
| vendor_nitku | FS-CV-05 → 22 digits |
| amount_in_words | FS-CV-07 → int if parseable, else whitespace-collapsed casefolded text |
| doc_number, po_reference | uppercase, remove whitespace; keep `/ - .` (do **not** over-normalize) |
| vendor_name, payer_name, received_by | casefold, strip punctuation, drop leading legal/shop forms (`pt`, `cv`, `ud`, `tb`, `toko`), collapse spaces |
| qty | `Decimal`, comma or dot decimal, strip trailing zeros |
| unit | lowercase + synonym map (`rules/units.yaml`) |

**Contract.** Parse failure returns `NormalizedValue(ok=False, raw=…, error_code=…)` — it never raises, so one bad
field does not hide the others. `fields_equal` on two failures compares the raw normalized text.

---

## 3. Confidence and abstention — `[LEARNING-CRITICAL]` — CP-18, CP-19

Runtime pieces live in `packages/core/src/cocok_core/confidence` (pure). Offline fitting/selection lives in
`packages/ml/src/cocok_ml/calibrate` (may use scikit-learn/scipy). The JSON in `rules/` is the hand-off.

### FS-CF-01 `build_signal_vector`  `[LEARNING-CRITICAL]` · CP-18 · `core/confidence/signals.py`
```python
SIGNALS_VERSION = "signals_v1"
FEATURE_NAMES: tuple[str, ...]   # fixed order, versioned
def build_signal_vector(field: str, ctx: SignalContext) -> SignalVector   # SignalVector(values: tuple[float, ...], names: tuple[str, ...], version: str)
```
**Inputs (`SignalContext`, all optional unless stated):** `primary_score` (exp(mean log-prob of the value tokens),
computed by the adapter), `self_consistency` (fraction of N samples agreeing), `amount_read` (value + seq prob;
`total_amount` only), `terbilang_value`, `issues` (from FS-CV-08), `ocr_agree` (FS-AD-07), `vendor_memory_value`,
`field_group` (money/date/id/text/lines).

**Feature set `signals_v1`:**

| name | value | missing encoding |
|---|---|---|
| `s_primary`, `m_primary` | primary_score ∈ [0,1] | 0, 1 |
| `s_selfcons`, `m_selfcons` | self-consistency ∈ [0,1] | 0, 1 |
| `s_amt_agree`, `m_amt_agree` | 1 if amount reader == primary (normalized) | 0, 1 (non-amount fields always missing) |
| `s_amt_prob` | amount-reader sequence prob | 0 |
| `s_terb_agree`, `m_terb_agree` | 1 if terbilang value == primary total | 0, 1 |
| `s_valid_ok` | 1 if no **blocking** issue touches this field | — |
| `s_arith_ok` | 1 if no arithmetic issue in the document | — |
| `s_ocr_agree`, `m_ocr_agree` | similarity ∈ [0,1] | 0, 1 |
| `g_<group>` | one-hot field group | — |

**Contract.** Pure; output length/order exactly `FEATURE_NAMES`; never NaN (assert). Changing the set bumps
`SIGNALS_VERSION` (and forces a refit — FS-CF-02 checks it).
**Tests.** Missing-signal encoding; ordering stable; a field with no signals at all → all `m_* = 1`.

### FS-CF-02 `apply_calibrator`  `[LEARNING-CRITICAL]` · CP-18 · `core/confidence/calibrator.py`
`def apply_calibrator(model: CalibratorModel, v: SignalVector) -> float`
* **Model JSON:** `{version, signals_version, kind: "logistic", feature_names, coef, intercept}` or
  `{version, signals_version, kind: "isotonic", input: "logit_of_logistic"|"s_primary", x: [...], y: [...]}`.
* **Contract.** Pure; raises `CalibratorMismatch` if `signals_version`/`feature_names` differ from the vector;
  numerically stable sigmoid (no overflow for |z| > 700); isotonic = piecewise-linear interpolation, clamped at the
  ends; output clipped to `[1e-6, 1 − 1e-6]`.
* **Tests.** Parity with scikit-learn `predict_proba` on 1 000 random vectors (|Δ| < 1e-9); monotonic in each
  positive-coefficient feature; JSON round trip.

### FS-CF-03 `decide_document`  `[LEARNING-CRITICAL]` · CP-19 · `core/confidence/policy.py`
```python
def decide_document(fields: Mapping[str, FieldDecisionInput], *, doc_type: DocType, issues: Sequence[Issue],
                    match_status: MatchStatus | None, policy: Policy) -> Decision
# Decision(status: Literal["AUTO_APPROVED","NEEDS_REVIEW"], reasons: tuple[Reason, ...])
```
**Contract.** Pure. Collects **all** reasons (the UI shows them), sorted. AUTO_APPROVED iff no reasons.

| Reason code | When |
|---|---|
| `AUTOMATION_DISABLED` | `policy.auto_approve_enabled` is false (kill switch) |
| `MISSING_REQUIRED` | required field absent or `NormalizedValue.ok == False` |
| `LOW_CONFIDENCE` | required field confidence < `policy.tau` (field named in reason) |
| `BLOCKING_ISSUE` | any issue with severity `blocking` (code named) |
| `MATCH_DISCREPANCY` | `match_status ∈ policy.blocking_match_statuses` |

**Tests.** One test per reason; combination test (three reasons at once → all three, sorted); τ boundary
(confidence == τ → accepted, i.e. `≥ τ`).

### FS-CF-04 `fit_calibrator`  `[LEARNING-CRITICAL]` · CP-18 · `ml/calibrate/fit.py`
```python
def fit_calibrator(X: np.ndarray, y: np.ndarray, groups: np.ndarray, feature_names: Sequence[str], *,
                   signals_version: str, seed: int, n_splits: int = 5) -> tuple[CalibratorModel, FitReport]
```
* `y[i] = 1` iff the field is correct by FS-CV-10; `groups` = document ids (use **grouped** K-fold so one
  document never sits in train and validation folds at once).
* Candidates: logistic regression (L2; `C ∈ {0.01, 0.1, 1, 10}` chosen in an inner grouped CV) and isotonic on the
  logistic logit. Choose by mean out-of-fold log-loss; tie → logistic.
* **Never re-balance classes** (it destroys calibration).
* `FitReport`: per-fold log-loss, Brier, ECE (FS-EV-03), chosen kind, `C`.
* **Tests.** Deterministic with seed; recovers known coefficients on synthetic logistic data (tolerance);
  serialized model passes FS-CF-02 parity.

### FS-CF-05 `select_threshold_sgr`  `[LEARNING-CRITICAL]` · CP-19 · `ml/calibrate/sgr.py`
```python
def select_threshold_sgr(doc_conf: Sequence[float], doc_err: Sequence[bool], *, target: float = 0.01,
                         delta: float = 0.05) -> SgrResult
# SgrResult(feasible: bool, tau: float, coverage: float, n_accepted: int, k_errors: int, ucb: float, steps: int)
```
**Purpose.** Pick the lowest τ (= highest coverage) whose risk among accepted documents is ≤ `target` with
probability ≥ 1 − δ (Selection with Guaranteed Risk, Geifman & El-Yaniv 2017; ADR-0007).

**Definitions.** `doc_conf[i]` = min calibrated confidence over the document's required fields (consistent with
FS-CF-03: a document is accepted iff every required field ≥ τ). `doc_err[i]` = any required field wrong.

**Approach notes (hints).** Sort documents by `doc_conf` descending; candidate thresholds are the distinct
confidence values. Binary-search the candidate index for `m = ⌈log₂ n⌉` steps; at each step compute the
Clopper–Pearson **upper** bound (FS-EV-06) of the error rate among accepted documents at level `δ / m`
(Bonferroni over the steps); move toward more coverage when the bound is ≤ target, otherwise toward less.
Return the best passing candidate; if none passes → `feasible=False`, `tau=+inf`, `coverage=0`.

**Examples.** 1 000 documents all correct with distinct confidences → feasible, coverage 1.0 if
`UCB(0, 1000, δ/m) ≤ 0.01` (it is: ≈ 0.0053 with m = 10, δ/m = 0.005). 200 documents all correct →
infeasible at target 0.01 (UCB(0, 200, 0.05) ≈ 0.0149 even before the Bonferroni split). With the split,
zero-error certification at 1 % needs ≈ 528 accepted documents when n ≈ 500–1 000 (m = 9–10).
**Tests.** Examples; **simulation test (SLOW):** 1 000 synthetic datasets with a known monotone error curve —
the selected τ's true risk exceeds `target` in ≤ 5 % of runs.

---

## 4. PO matching — `[LEARNING-CRITICAL]` — CP-24 (`packages/core/src/cocok_core/matching`)

### FS-MT-01 `resolve_po`
`def resolve_po(doc: ExtractedDocument, candidates: Sequence[PurchaseOrder], *, window_days: int) -> PoResolution`
* Order: (1) normalized `po_reference` equality → `FOUND_BY_REFERENCE`; (2) vendor key (NPWP16, else normalized
  name per FS-CV-10) + open POs with `po_date ≤ doc_date ≤ po_date + window_days` → exactly one:
  `FOUND_BY_VENDOR_WINDOW`; more than one: `AMBIGUOUS` (pick none — a human decides); none: `NOT_FOUND`.
* Returns the candidates considered (for UI evidence). Pure.

### FS-MT-02 `normalize_item_description`
`def normalize_item_description(text: str, *, units: UnitSynonyms) -> NormalizedItem` — `tokens`, `numbers`, `unit`.
* casefold; strip punctuation; split number–unit (`40kg` → `40 kg`); unit synonyms from `rules/units.yaml`
  (`zak→sak`, `btg|bt→batang`, `m³|kubik→m3`, `kilo→kg`, `bh|buah|pcs→pcs`, `box|karton→dus`, `lbr→lembar`).
* Examples: `"SEMEN GRESIK 40KG"` and `"Semen Gresik 40 kg"` → identical tokens.

### FS-MT-03 `align_lines`
`def align_lines(doc_lines, po_lines, *, min_similarity: float) -> list[LinePair]` — `LinePair(doc_idx|None, po_idx|None, similarity)`
* Similarity: token-set ratio (rapidfuzz) of normalized descriptions, + small bonus when units match, − penalty
  when embedded numbers (sizes like 40 kg vs 50 kg) differ.
* Assignment must be **globally optimal** on the similarity matrix (Hungarian algorithm or an exact method for
  small n); pairs below `min_similarity` become unmatched on both sides. Deterministic tie-breaking by index.
* Hint: write the cost matrix first and test it alone; then the assignment.

### FS-MT-04 `compare_pair`
`def compare_pair(doc_line: LineItem, po_line: PoLine, *, tol: MatchTolerances) -> list[Discrepancy]`
* Codes: `QTY_OVER`, `QTY_UNDER` (relative tolerance), `PRICE_HIGHER`, `PRICE_LOWER` (relative and absolute
  tolerance), `UNIT_MISMATCH`. Each discrepancy carries expected/actual values for the UI.

### FS-MT-05 `three_way_match`
`def three_way_match(po: PurchaseOrder, invoice: ExtractedDocument, delivery: ExtractedDocument | None, *, tol) -> MatchResult`
* Checks per aligned line: invoice qty ≤ delivered qty ≤ ordered qty (within tolerance); invoice price ≈ PO price.
* Status: `MATCHED`, `MATCHED_WITH_DISCREPANCIES`, `NO_PO`, `AMBIGUOUS_PO`, `NO_DELIVERY` (two-way checks only,
  flagged), plus line-level `UNMATCHED_DOC_LINE` / `UNMATCHED_PO_LINE`.

### FS-MT-06 `detect_duplicate`
`def detect_duplicate(doc: ExtractedDocument, history: Iterable[DocKey]) -> DuplicateFinding | None`
* Exact: same `(vendor_key, normalized doc_number, doc_date.year)` → `DUPLICATE_DOC_NUMBER` (blocking).
* Near: same vendor + same total + same date, different number → `POSSIBLE_DUPLICATE` (warning).

---

## 5. Evaluation

### 5.1 Metric functions — `[LEARNING-CRITICAL]` — CP-11 (`packages/ml/src/cocok_ml/eval/metrics`)

#### FS-EV-01 `field_accuracy`
`def field_accuracy(pred: Sequence[ItemPrediction], gt: Sequence[ItemTruth], *, fields: Sequence[str], by: Sequence[str] = ("tier","doc_type")) -> pd.DataFrame`
* Correct = `fields_equal` (FS-CV-10). GT null & pred null → correct. GT null & pred non-null → wrong **and**
  counted in `hallucination_rate`. Pred missing / parse failure → wrong.
* `line_items`: micro precision/recall/F1 over tuples `(normalized description, qty, line_total)` matched with
  FS-MT-03 (reuse; do not reinvent).
* Output columns: `group…, field, n, correct, acc, ci_low, ci_high` (Clopper–Pearson, FS-EV-06).

#### FS-EV-02 `amount_exact_match`
Same as FS-EV-01 restricted to `total_amount`, reported per tier with CI. Example: 45/50 correct →
acc 0.90, 95 % CI [0.782, 0.967].

#### FS-EV-03 `expected_calibration_error`
`def expected_calibration_error(conf: ArrayLike, correct: ArrayLike, n_bins: int = 15) -> tuple[float, list[Bin]]`
* Equal-width bins on [0, 1]; the last bin includes 1.0; empty bins contribute 0.
  `ECE = Σ_b (n_b / N) · |acc_b − mean_conf_b|`.
* **Worked example (2 bins):** conf `[0.9, 0.9, 0.8, 0.3]`, correct `[1, 0, 1, 0]` → bin [0, 0.5): |0 − 0.3|·¼ =
  0.075; bin [0.5, 1]: |⅔ − 0.8667|·¾ = 0.15 → **ECE = 0.225**.

#### FS-EV-04 `risk_coverage_curve`
`def risk_coverage_curve(doc_conf, doc_err) -> list[RcPoint]` — `RcPoint(tau, coverage, risk, n_accepted, k_errors)`
* Sort by confidence descending; **group ties** (all documents with the same confidence enter together).
* Example: conf `[0.9, 0.8, 0.8, 0.6]`, err `[0, 0, 1, 1]` → (τ 0.9, cov 0.25, risk 0), (τ 0.8, cov 0.75,
  risk ⅓), (τ 0.6, cov 1.0, risk 0.5).

#### FS-EV-05 `aurc`, `automation_rate_at_risk`
* `aurc(points)`: item-weighted mean of risk over accepted prefixes, ties sharing their group's risk.
  Example above → (0 + ⅓ + ⅓ + 0.5) / 4 = **0.2917**.
* `automation_rate_at_risk(points, target)` → max coverage with empirical risk ≤ target (the *empirical* headline);
  the *certified* headline comes from FS-CF-05 on calib, evaluated on test.

#### FS-EV-06 `clopper_pearson`
`def clopper_pearson(k: int, n: int, *, alpha: float = 0.05, side: Literal["two","upper","lower"] = "two") -> tuple[float, float]`
* Upper (one-sided) = `Beta⁻¹(1 − α; k + 1, n − k)`, = 1 if k = n. Lower = `Beta⁻¹(α; k, n − k + 1)`, = 0 if k = 0.
  Two-sided uses α/2 on each side. `n = 0` → `ValueError`.
* **Oracle values (α = 0.05, upper):** (0, 299) → 0.009969 · (0, 298) → 0.010002 · (1, 473) → 0.009990 ·
  (1, 472) → 0.010011 · (0, 10) → 0.258866 · (5, 10) → 0.777559.

#### FS-EV-07 `cluster_bootstrap_ci`
`def cluster_bootstrap_ci(metric: Callable[[Items], float], items: Items, *, cluster_key: str = "document_id", n_boot: int = 2000, alpha: float = 0.05, seed: int) -> tuple[float, float]`
* Resample **documents** with replacement (not fields); percentile interval; deterministic with seed.

#### FS-EV-08 `discrepancy_prf`
Per discrepancy code: precision, recall, F1 (with Clopper–Pearson CIs for P and R) matching predicted issues to
planted labels by `(document_id, code)`.

### 5.2 Eval harness — agent-owned (R2) — CP-11, CP-31

#### FS-EH-01 `run_eval`
`cocok-eval run --route <id> --tiers T0,T1,T2,T3 --out evals/results/<run_id>/ [--max-cost-usd 5] [--resume]`
* Loads items from the dataset manifest; **provider policy guard**: `evals/configs/providers.yaml` maps tier →
  allowed providers; refuses (exit code 3) to send `T3`/`orand_car` images to free-tier providers.
* Writes one JSONL prediction per item (format in CHECKPOINTS CP-11), the raw output cache, `metrics.json`
  (all FS-EV metrics with CIs), `report.md`, plots. Resumable (skips done items). Stops at the cost cap.
* Records `code_sha`, dataset version, model id + revision, prompt id/version, rules version.

#### FS-EH-02 `replay`
`cocok-eval replay --from <run_id> --tiers …` — re-runs normalization → validators → signals → calibrator →
policy on cached raw outputs; zero network. Output identical to `run` for unchanged code (byte-identical
`metrics.json`).

#### FS-EH-03 report writer
Markdown + PNG plots; every metric row has a CI; `n < 30` cells labeled *indicative*; risk–coverage plot shows the
empirical and the certified operating points.

#### FS-EH-04 `gate_compare`
`cocok-eval gate --mode replay|live --baseline evals/baseline.json --config evals/gate.yaml`
* Replay mode: fail if certified automation rate decreases or a critical field's CI upper bound < baseline point.
* Live mode: paired comparison on the fixed 30-doc set; fail if `wrong_now − wrong_baseline ≥ 2`; cost cap.
* Exit codes: 0 pass, 1 regression, 2 configuration error, 3 policy violation.

---

## 6. Machine learning

### 6.1 CRNN amount reader — `[LEARNING-CRITICAL]` — CP-14 (`packages/ml/src/cocok_ml/train/crnn`)

#### FS-CR-01 `CharsetCodec`
`CharsetCodec(charset: str)`; `encode(text) -> list[int]`; `decode(indices) -> str`.
* Index 0 is reserved for the CTC **blank**; characters map to 1…C. Unknown char → `ValueError`.
* Amount charset: `"0123456789.,-Rp "`; names charset: built from the `names` train split (record it in MLflow).
* Tests: `decode(encode(s)) == s` (Hypothesis over the charset).

#### FS-CR-02 `CRNN`
`class CRNN(nn.Module): forward(x: Tensor[B,1,32,W]) -> Tensor[T,B,C+1]` (log-probabilities over classes incl. blank)
* Constraints (not a full design): convolutional feature extractor that collapses height 32 → 1 and downsamples
  width by **4** (so `T = W // 4`); 2-layer bidirectional LSTM (hidden 256 per direction); linear projection to
  `C + 1`; `log_softmax` on the class dimension. ≤ 10 M parameters (CPU budget). `input_lengths` per sample =
  `true_width // 4`.
* Pretrain/fine-tune: replace only the final projection when switching from the names charset to the amount
  charset; document which layers are frozen.
* Tests: shape test for W ∈ {64, 128, 257}; parameter count ≤ 10 M; deterministic forward in eval mode.

#### FS-CR-03 `ctc_greedy_decode`
`def ctc_greedy_decode(log_probs: Tensor[T,B,C], lengths: Tensor[B], codec: CharsetCodec) -> list[DecodeResult]`
— `DecodeResult(text, mean_max_logprob, path_logprob)`
* Per time step take the argmax; collapse consecutive repeats; remove blanks; respect each sample's length.
* Examples (charset `"12"`, blank 0): argmax `[1,1,0,2,2]` → `"12"`; `[1,0,1]` → `"11"`; `[0,0,0]` → `""`.
* Confidence fields feed FS-CF-01 (`s_amt_prob` uses `exp(mean_max_logprob)`).

#### FS-CR-04 `train_one_epoch` / `evaluate`
* `train_one_epoch(model, loader, optimizer, scheduler, *, clip=5.0, device) -> EpochStats(loss, n, grad_norm_mean)`
  uses `nn.CTCLoss(blank=0, reduction="mean")` with true `input_lengths`/`target_lengths`; gradient clipping;
  no silent `zero_infinity` (assert finite loss; on inf raise with the offending sample ids).
* `evaluate(model, loader) -> EvalStats(exact_match, cer, n)`; exact match compares **normalized money**
  (FS-CV-01) when both parse, else raw strings.
* Test: overfits 64 samples to 100 % exact match (SLOW).

#### FS-CR-05 `export_onnx` + parity — agent-owned (R2) · `ml/train/export_onnx.py` (shared with TrOCR)
`export_onnx(model, path, *, opset=17)` with dynamic axes for batch and width; `check_parity(model, onnx_path, crops) -> float`
(max |Δlogit|; must be < 1e-3). `model.eval()` enforced.

### 6.2 Data generation — agent-owned (R2) — CP-05…CP-10 (`packages/ml/src/cocok_ml/datagen`)

| ID | Function | Contract highlights |
|---|---|---|
| FS-DG-01 | `generate_scenario(seed: int, config: GenConfig) -> Scenario` | Deterministic per seed; ground truth = `ExtractedDocument` + PO + delivery; uses core `to_terbilang`, `format_money`, `compute_ppn` (no re-implementation); identifiers random and fictional |
| FS-DG-02 | `plant_perturbation(s: Scenario, kind: PerturbationKind, rng) -> tuple[Scenario, PerturbationLabel]` | Kinds = blueprint §4.2 list; magnitude always exceeds tolerances; label records expected issue code(s) |
| FS-DG-03 | `render_digital(s, template, out_dir) -> RenderResult` | PDF with text layer + page PNGs (200 DPI); field bboxes normalized, top-left origin |
| FS-DG-04 | `render_handwriting_like(s, font, rng) -> RenderResult` | Training-only flag in manifest |
| FS-DG-05 | `render_composite(s, crops: CropSource, rng) -> RenderResult` | Records `source_item_ids`; output license = most restrictive input; refuses `orand_car` (`LicenseViolation`) |
| FS-DG-06 | `photo_sim(image, boxes, rng, ops: Sequence[OpSpec]) -> (image, boxes, params_used)` | Every op pure + seeded; geometric ops transform boxes with the same matrix/field |
| FS-DG-07 | `build_manifest(source_id, files) -> pd.DataFrame` | Columns per blueprint §4.5; sha256 of raw bytes; license never null |
| FS-DG-08 | `leakage_check(manifests) -> LeakageReport` | Fails on sha256 or `source_item_id` overlap between {train, calib} and any test tier; CLI exit 1 on leakage |
| FS-DG-09 | `publish(dataset, *, dry_run) -> PublishPlan` | Refuses ND / non-publishable sources; writes dataset-card counts; never uploads without `--confirm` |
| FS-DG-10 | `make_scenario_sheet(s) -> bytes (PDF)` | A5 printable sheet for T3 handwriting: values to write, style hint, capture condition, scenario id |

### 6.3 VLM LoRA (agent-owned, R2) — CP-17 — notes that are easy to get wrong
* Target JSON: schema key order, integers for money, `null` for absent fields, no extra keys.
* Labels: `-100` on every non-assistant token (verify by decoding labels in a unit test).
* Image resolution: cap max pixels (the main VRAM lever); record it in the run config.
* Inference wrapper returns `ExtractionResult` exactly like API adapters, plus per-token log-probs when available
  (→ `primary_score`).

---

## 7. Adapters — agent-owned (R3, R2) — CP-16, CP-21, CP-22 (`packages/adapters/src/cocok_adapters`)

### FS-AD-01 `LLMClient.structured` (OpenAI / Gemini / Bedrock / Kaggle proxy)
`async def structured(req: StructuredRequest) -> StructuredResponse`
— `StructuredRequest(prompt_id, prompt_version, system, user_parts (text|image bytes), json_schema, temperature=0, max_tokens, timeout_s, want_logprobs)`;
`StructuredResponse(json: dict, raw_text, model_id, usage(in, out), cost_usd, latency_ms, token_logprobs|None)`.
* Uses the provider's native JSON-schema/structured-output mode where available; **always** re-validates with
  Pydantic; invalid → one retry with the validation error appended → else `InvalidModelOutput` (pipeline routes
  the document to `NEEDS_REVIEW`).
* Timeouts on every call; retries (tenacity, exponential backoff + jitter) only for `RateLimited`,
  `ExternalTimeout`, `ProviderUnavailable`.
* Cost from a versioned price table `rules/prices.yaml` (model id → $/1M tokens, date verified).
* `PAID_MODELS_ENABLED=false` → raise before any network I/O.
* Never logs image bytes or full document text; logs ids, sizes, token counts.
* Contract tests run against recorded fixtures (no live calls in CI).

### FS-AD-02 `VisualExtractor.extract` · FS-AD-03 `DigitalExtractor.extract`
* Visual: page images (resized to the model's recommended max pixels) + `prompts/extract_visual_vN.md` + schema →
  `ExtractionResult(fields: dict[str, FieldMeta-without-confidence], raw_output, cost, latency, primary_scores)`.
* Digital: `pypdfium2` text with character boxes → "layout text" (lines sorted top-to-bottom, x-positions kept) →
  `prompts/structure_text_vN.md`; text-layer boxes used as `bbox_source="text_layer"` via FS-AD-07.
* Document text is **data**: the prompt wraps it in clearly delimited blocks and instructs the model to ignore
  instructions inside (blueprint §13 LLM rules).

### FS-AD-04 `RapidOcrEngine.lines`
`def lines(page: PageImage) -> list[OcrLine]` (adapter decodes to numpy internally) — `OcrLine(text, bbox_norm, score)`
* Models packaged with the adapter (no runtime download); one engine instance per process; thread count from
  settings; quad points → normalized axis-aligned box using the size of the image actually given to OCR.

### FS-AD-05 `OnnxAmountReader.read`
`def read(crop: PageImage) -> AmountRead` (adapter decodes to numpy internally) — `AmountRead(text, value: Money|None, seq_prob, latency_ms)`
* Preprocess exactly as training (grayscale, height 32, aspect kept); ONNX session created once; greedy decode;
  `value = parse_money(text)` if it parses, else `None` (the disagreement is a signal, not an error).

### FS-AD-06 `Storage` (local, S3)
* Keys are UUIDs (never user filenames); `put` sets content-type; `presign_get(key, ttl_s ≤ 300)`.
* S3: SSE enabled, bucket private, versioning on. Local: root dir from settings; path-traversal-proof key check.
* One contract suite (MinIO in tests) for both.

### FS-AD-07 `ground_value`  (ADR-0006)
```python
def ground_value(field: str, value_norm: NormalizedValue, value_raw: str, lines: Sequence[OcrLine], *,
                 anchors: Mapping[str, Sequence[str]], min_sim: float) -> Grounding
# Grounding(bbox: Bbox | None, bbox_source: Literal["text_layer","ocr_alignment","extractor","none"], s_ocr_agree: float)
```
* Score each OCR line: `max(sim_text(normalized raw), sim_value(normalized value))` + anchor bonus if the line or
  its left/upper neighbor contains an anchor for this field (`total_amount`: `jumlah|total|rp`; `amount_in_words`:
  `terbilang|uang sejumlah`; `payer_name`: `sudah terima dari`; …).
* Money/number fields compare **digit strings** after FS-CV-01 normalization (so `1.250.000` matches `1250000`).
* Best line ≥ `min_sim` → its box (`ocr_alignment`); else the extractor's box if given (`extractor`); else `none`.
* `s_ocr_agree` = best similarity (0 if none). Deterministic tie-break: higher score, then top-most, then left-most.
* Golden tests: 10 fixtures with expected boxes; "no match" fixture returns `none`.

### FS-AD-08 Repositories (SQLAlchemy 2 async + psycopg 3)
`DocumentRepository`, `ExtractionRepository`, `PurchaseOrderRepository`, `UserRepository`, `SessionRepository`,
`AuditRepository`, `VendorMemoryRepository`.
* Return domain types, not ORM objects. All writes for one use case happen in one transaction passed in by the
  service (unit-of-work), so FSM transition + job enqueue + audit are atomic.
* `AuditRepository` has `append` only (no update/delete methods — mirrors DB grants).

### FS-AD-09 `ProcrastinateQueue.enqueue_in_tx`  (ADR-0004)
`async def enqueue_in_tx(conn, task: str, args: dict, lock: str) -> str | None`
* Uses the caller's connection/transaction; `queueing_lock=lock` (`f"{sha256}:{pipeline_version}"`); returns job id
  or `None` if an identical job is already queued (idempotent).
* Contract tests: rollback → no job; double enqueue → one job.

### FS-AD-10 `SystemClock`, `UuidV7Generator`
* `now()` returns tz-aware UTC; `new()` returns UUIDv7 via `uuid-utils`; fakes for tests (`FrozenClock`,
  `SequentialIds`).

---

## 8. Worker pipeline — agent-owned (R3) — CP-23 (`apps/worker/src/cocok_worker`)

### FS-WK-01 `build_graph`
`def build_graph(deps: WorkerDeps, checkpointer) -> CompiledGraph`
* Nodes (one file each): `ingest, detect_input_kind, classify_doc_type, route, extract, ground, read_amount,
  validate, score_confidence, match_against_po, decide, persist, emit_events`; linear except `route`
  (digital/visual branch). **No `interrupt()`** (ADR-0005). State = Pydantic model; new keys optional.

| Node | Input → Output (state keys) | Side effects |
|---|---|---|
| ingest | document_id → file meta, page images (bytes refs) | read from Storage |
| detect_input_kind | pages → `input_kind` (FS-WK-02) | — |
| classify_doc_type | text/pages → `doc_type`, `doc_type_conf` (FS-WK-03) | maybe 1 cheap LLM call |
| route | input_kind, doc_type → `route_id` | — |
| extract | route → `extraction` | paid LLM/VLM call (cost recorded) |
| ground | extraction, pages → bboxes, `s_ocr_agree` (FS-AD-07) | CPU OCR |
| read_amount | total_amount bbox → `amount_read` (FS-AD-05) | CPU ONNX |
| validate | extraction → normalized values, `issues` (FS-CV-08/10) | — |
| score_confidence | signals → calibrated confidences (FS-CF-01/02) | — |
| match_against_po | doc → `match_result` (FS-MT-*) | DB read |
| decide | all → `decision` (FS-CF-03) | — |
| persist | all → rows + FSM transition (FS-WK-05) | **DB write (one tx)** |
| emit_events | → audit entries, metrics | DB write |

### FS-WK-02 `detect_input_kind`
* PDF with ≥ `settings.min_text_chars_per_page` extractable characters on every page → `digital`; otherwise
  `visual` (scanned PDF pages rasterized at 200 DPI). Images → `visual`. Encrypted/corrupt PDF → permanent error.

### FS-WK-03 `classify_doc_type`
* Rules first (keywords on text layer or OCR lines: `FAKTUR`, `INVOICE`, `KWITANSI`/`TANDA TERIMA`,
  `SURAT JALAN`/`DELIVERY`, `NOTA`); if no rule fires or two conflict → one cheap model call; record which path
  decided and its confidence (low confidence → `NEEDS_REVIEW` reason `UNCERTAIN_DOC_TYPE`).

### FS-WK-04 `node` wrapper (decorator)
* Applies per-node timeout, OpenTelemetry span (`node.name`, `document_id`, `pipeline_version`), structured log on
  enter/exit, maps exceptions: `RetryableError` → re-raise for the queue's retry; other `DomainError` → mark run
  failed with `code`; unknown → `FAILED` with `INTERNAL_ERROR` (and Sentry).
* Nodes are pure w.r.t. external state except `persist`/`emit_events` (crash-resume safety).

### FS-WK-05 `persist`
* In **one transaction**: insert `extraction_runs` + `extracted_fields` + `match_results`; FSM transition
  `PROCESSING → EXTRACTED → AUTO_APPROVED|NEEDS_REVIEW` via FS-CM-02; audit entries. Idempotent: a second call
  for the same `(document_id, pipeline_version)` is a no-op.

---

## 9. API — agent-owned (R3, reviewed by R7) — CP-25 (`apps/api/src/cocok_api`)

| ID | Function / endpoint | Contract highlights |
|---|---|---|
| FS-AP-01 | `upload_document` (`POST /documents`) | Magic-byte allowlist (PDF/JPEG/PNG/WEBP); size ≤ 10 MB; pages ≤ 10; pixel limit; images re-encoded; PDF never executed; storage key = UUID; dedupe by sha256 (returns existing document); `Idempotency-Key` (same key + same body → same response; same key + different body → 409); status UPLOADED → QUEUED and job enqueued **in one transaction**; 202 `{document_id, job_id}` |
| FS-AP-02 | `correct_field` (`PATCH …/fields/{field}`) | Role ≥ staff; reason required (≤ 500 chars); re-normalizes with FS-CV-10; stores `corrections` row + audit (before/after); re-runs validators for the document; does not change FSM state |
| FS-AP-03 | `approve` / `reject` | Role ≥ manager; FSM via FS-CM-02 (invalid → 409 problem+json); audit; optional `POST` → POSTED later |
| FS-AP-04 | `review_queue` | `NEEDS_REVIEW` only; sort by min required-field confidence asc; filters doc_type/vendor; **cursor** pagination (opaque, signed); stable order (confidence, id) |
| FS-AP-05 | `login` / `logout` / `current_user` | pwdlib argon2id verify + rehash-if-needed; constant-time failure path; session id 256-bit random, DB stores sha256; cookie attributes per ADR-0008; id rotated on login; logout revokes row; rate-limited |
| FS-AP-06 | `verify_csrf` (dependency) | For unsafe methods: header token == cookie token (double submit) **and** `Origin` ∈ allowlist; else 403 problem+json |
| FS-AP-07 | `require_role(min_role)` (dependency) | Role order viewer < staff < manager < admin; role change revokes the user's sessions; denial → 403 |
| FS-AP-08 | error mapping | `DomainError.code` → RFC 9457 problem+json (`type`, `title`, `status`, `detail`, `code`, `instance`=request id); never stack traces |
| FS-AP-09 | `/healthz`, `/readyz` | healthz: process alive; readyz: DB query < 200 ms, storage head-bucket, worker heartbeat < 60 s old → 200 else 503 with failing component |

---

## 10. Vendor memory — agent-owned (R3) — CP-32

### FS-VM-01 `lookup_vendor_memory` / `record_correction`
* Lookup order: exact normalized NPWP → `pg_trgm` similarity on normalized vendor name ≥ threshold → none.
  **No embeddings** unless an ADR shows benefit (blueprint §5.7).
* Returns up to k recent corrected examples (field, raw, corrected) for few-shot prompting and a per-field prior
  value for the `s_vendor_mem` signal.
* `record_correction` stores the correction and creates a regression case under `evals/regression/<vendor_key>/`.

---

## 11. Web — agent-owned (R4) — CP-26, CP-27 (`apps/web`)

### FS-WB-01 `bboxToViewport`
`function bboxToViewport(b: Bbox, page: PageLayout, view: ViewTransform): Rect`
* Input normalized `[page, x0, y0, x1, y1]`; `PageLayout` = rendered page rect (from `getBoundingClientRect`) and
  cumulative page offsets; `ViewTransform` = zoom, pan, rotation (0/90/180/270).
* Pure; unit tests for each rotation, zoom 0.5/1/2, page 2 of 3.

### FS-WB-02 `useReviewShortcuts`
* `j/k` next/previous field · `Enter` accept field · `e` edit · `a` approve (manager) · `r` reject · `n` next
  document · `?` help overlay. Disabled while typing in inputs. Announced to screen readers.

### FS-WB-03 upload queue
* One `Idempotency-Key` (UUID) per file, persisted for retry; per-file states `queued → uploading → accepted |
  failed(reason)`; concurrency 2; retries only on network errors/5xx.

---

## 12. Operations scripts — agent-owned (R5) — CP-30, CP-31 (`infra/scripts`)

| ID | Script | Contract |
|---|---|---|
| FS-OP-01 | `deploy.sh <sha>` | `set -euo pipefail`; backup (FS-OP-03) → pull images by SHA → `alembic upgrade head` (migrator role) → `compose up -d` → poll `/readyz` (timeout 120 s) → on failure run `rollback.sh <previous_sha>` and exit 1; writes a deploy log line (sha, duration, result) |
| FS-OP-02 | `rollback.sh <sha>` | Re-deploys a previous image SHA (last 5 kept); **does not** downgrade the DB (expand/contract rule makes old code compatible); verifies readiness |
| FS-OP-03 | `backup.sh` | `pg_dump -Fc` → `age` encrypt (public key from SSM) → S3 key `backups/YYYY/MM/DD/<ts>.dump.age`; verifies upload size > 0; prints object key |
| FS-OP-04 | `restore.sh <object_key> <target_db>` | Refuses to target the production DB name; download → decrypt (private key provided interactively/out of band) → `pg_restore` into scratch DB → smoke queries (row counts, latest document) → prints elapsed time for RTO log |

---

## Appendix A — Traceability matrix

| FS-ID | Owner | Checkpoint | Module |
|---|---|---|---|
| FS-CM-01…05 | Agent R3 | CP-02 | `core/models`, `core/errors.py`, `core/ports` |
| FS-CV-01…05 | AI · Arka studies + tests | CP-03 | `core/validation/{money,dates,npwp}.py` |
| FS-CV-06…10 | AI (loader R3) · Arka studies + tests | CP-04 | `core/validation/{terbilang,arithmetic,tax,fields}.py` |
| FS-DG-07, 08 | Agent R2 | CP-05 | `ml/datagen/{manifest,leakage}.py` |
| FS-DG-01, 02, 10 | Agent R2 | CP-06 | `ml/datagen/{scenario,perturb,sheet}.py` |
| FS-DG-03 | Agent R2 | CP-07 | `ml/datagen/render_digital.py` |
| FS-DG-04…06 | Agent R2 | CP-08 | `ml/datagen/{render_handwriting,render_composite,photo_sim}.py` |
| FS-DG-09 | Agent R2 | CP-10 | `ml/datagen/publish.py` |
| FS-EV-01…08 | AI · Arka studies + tests | CP-11 | `ml/eval/metrics/*` |
| FS-EH-01…03 | Agent R2 | CP-11 | `ml/eval/{runner,replay,report}.py` |
| FS-CR-01…04 | AI · Arka studies + tests | CP-14 | `ml/train/crnn/*` |
| FS-CR-05 | Agent R2 | CP-14/15 | `ml/train/export_onnx.py` |
| FS-AD-04, 07 | Agent R3/R2 | CP-16 | `adapters/{ocr/rapidocr,grounding/align}.py` |
| FS-CF-01, 02, 04 | AI · Arka studies + tests | CP-18 | `core/confidence/{signals,calibrator}.py`, `ml/calibrate/fit.py` |
| FS-CF-03, 05 | AI · Arka studies + tests | CP-19 | `core/confidence/policy.py`, `ml/calibrate/sgr.py` |
| FS-AD-08, 10 | Agent R3 | CP-21 | `adapters/db/*` |
| FS-AD-01…03, 05, 06, 09 | Agent R3 | CP-22 | `adapters/{llm,storage,amount_reader,queue}/*` |
| FS-WK-01…05 | Agent R3 | CP-23 | `apps/worker/*` |
| FS-MT-01…06 | AI · Arka studies + tests | CP-24 | `core/matching/*` |
| FS-AP-01…09 | Agent R3 (+R7) | CP-25 | `apps/api/*` |
| FS-WB-03 | Agent R4 | CP-26 | `apps/web/src/features/upload/*` |
| FS-WB-01, 02 | Agent R4 | CP-27 | `apps/web/src/components/review/*` |
| FS-OP-01, 02 | Agent R5 | CP-30 | `infra/scripts/{deploy,rollback}.sh` |
| FS-OP-03, 04, FS-EH-04 | Agent R5/R6 | CP-31 | `infra/scripts/{backup,restore}.sh`, `ml/eval/gate.py` |
| FS-VM-01 | Agent R3 | CP-32 | `adapters/db/vendor_memory.py`, `apps/api/services/vendor_memory.py` |

**Learning-critical total:** 10 (validation) + 5 (confidence) + 6 (matching) + 8 (metrics) + 4 (CRNN) = **33 functions** —
the part of Cocok Arka must be able to explain, test and defend in an interview (ADR-0014).
