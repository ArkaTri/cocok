"""Ports: the interfaces ``core`` needs from the outside world (FS-CM-05, ports & adapters).

A port is a ``typing.Protocol``: any class with matching methods satisfies it, without
inheritance. Adapters stay free of ``core`` base classes, and tests can use tiny fakes. Rules:

* Ports speak domain types only (``cocok_core`` types and the standard library), never SDK
  objects.
* Methods only, no mutable attributes (mutable attributes make Protocols invariant and awkward
  for mypy).
* ``async`` where the real implementation does I/O; plain ``def`` for CPU-bound work that the
  worker runs in a thread.

Repository ports (database access) are defined in CP-21/22 together with the database schema,
not guessed here.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from cocok_core.ports.types import (
    AmountRead,
    DocumentInput,
    ExtractionResult,
    OcrLine,
    PageImage,
    StructuredRequest,
    StructuredResponse,
    Transaction,
)


@runtime_checkable
class Extractor(Protocol):
    """Turns a document into structured fields (baselines B1-B4 and the fine-tuned VLM)."""

    async def extract(self, doc: DocumentInput) -> ExtractionResult:
        """Extract every field of the canonical schema from ``doc``."""
        ...


@runtime_checkable
class AmountReader(Protocol):
    """Reads the total amount from a crop (CRNN / TrOCR experiment, Milestone B)."""

    def read(self, crop: PageImage) -> AmountRead:
        """Read the digits in ``crop``."""
        ...


@runtime_checkable
class OcrEngine(Protocol):
    """Finds text lines with boxes; used to ground fields to locations (ADR-0006)."""

    def lines(self, page: PageImage) -> list[OcrLine]:
        """Return every text line on ``page``, top to bottom."""
        ...


@runtime_checkable
class Storage(Protocol):
    """Object storage for uploaded files and rendered pages."""

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        """Store ``data`` under ``key``, overwriting any previous object."""
        ...

    async def get(self, key: str) -> bytes:
        """Return the object stored under ``key``."""
        ...

    async def presign_get(self, key: str, ttl_s: int) -> str:
        """Return a time-limited URL the browser can download ``key`` from."""
        ...


@runtime_checkable
class LLMClient(Protocol):
    """Calls a hosted or local model and returns JSON that follows a schema."""

    async def structured(self, req: StructuredRequest) -> StructuredResponse:
        """Send ``req`` and return the parsed answer with usage and cost."""
        ...


@runtime_checkable
class JobQueue(Protocol):
    """Background job queue (Procrastinate on Postgres, ADR-0004)."""

    async def enqueue_in_tx(
        self, tx: Transaction, task: str, args: Mapping[str, object], lock: str
    ) -> str | None:
        """Enqueue ``task`` inside the caller's transaction.

        Returns:
            The job id, or ``None`` if a job with the same ``lock`` is already queued.
        """
        ...


@runtime_checkable
class Clock(Protocol):
    """Source of the current time (injected so tests can freeze it)."""

    def now(self) -> datetime:
        """Return the current time, timezone-aware, in UTC."""
        ...


@runtime_checkable
class IdGenerator(Protocol):
    """Source of new ids (injected so tests are deterministic)."""

    def new(self) -> UUID:
        """Return a new UUIDv7 (time-ordered, so database indexes stay compact)."""
        ...
