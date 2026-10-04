"""Data that crosses the ports (FS-CM-05): plain frozen dataclasses, no SDK objects, no numpy.

``core`` may not import numpy, so images cross as encoded bytes (:class:`PageImage`) and the
adapters decode them. Database transactions cross as the opaque :class:`Transaction` handle, so
``core`` never imports psycopg.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Final, Literal, Protocol
from uuid import UUID

from cocok_core.models.document import (
    DocType,
    ExtractedDocument,
    FieldMeta,
    check_box,
    is_valid_field_path,
)
from cocok_core.models.money import Money

ImageMime = Literal["image/png", "image/jpeg", "image/webp"]
_IMAGE_MIMES: Final = frozenset({"image/png", "image/jpeg", "image/webp"})


class Transaction(Protocol):
    """Opaque handle for an open database transaction.

    ``core`` never looks inside it. The Postgres adapter passes its own connection object
    through, and the queue adapter uses it to enqueue a job *in the same transaction* as the
    status change (ADR-0004), so a job can never exist without its status, or the reverse.
    """


@dataclass(frozen=True, slots=True)
class PageImage:
    """One encoded page image, or a crop of one.

    Args:
        data: Encoded bytes (PNG/JPEG/WebP). Hidden from ``repr`` to keep logs small.
        mime: The encoding of ``data``.
        width: Width in pixels, > 0.
        height: Height in pixels, > 0.
        page: 0-based page index in the source document.

    Raises:
        ValueError: On empty data, unknown mime, non-positive size or negative page.
    """

    data: bytes = field(repr=False)
    mime: ImageMime
    width: int
    height: int
    page: int = 0

    def __post_init__(self) -> None:
        if not self.data:
            msg = "PageImage.data is empty"
            raise ValueError(msg)
        if self.mime not in _IMAGE_MIMES:
            msg = f"unsupported image mime {self.mime!r}"
            raise ValueError(msg)
        if self.width <= 0 or self.height <= 0:
            msg = f"image size must be positive, got {self.width}x{self.height}"
            raise ValueError(msg)
        if self.page < 0:
            msg = f"page must be >= 0, got {self.page}"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class DocumentInput:
    """Everything an extractor may look at for one document.

    Args:
        document_id: The document's UUIDv7.
        pages: Page images in order; at least one.
        doc_type_hint: Type chosen by the uploader, if any.
        page_texts: Text layer per page for digital PDFs (ADR-0010); empty for photos.

    Raises:
        ValueError: If there are no pages, or ``page_texts`` has a different length.
    """

    document_id: UUID
    pages: tuple[PageImage, ...]
    doc_type_hint: DocType | None = None
    page_texts: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.pages:
            msg = "DocumentInput needs at least one page"
            raise ValueError(msg)
        if self.page_texts and len(self.page_texts) != len(self.pages):
            msg = f"{len(self.page_texts)} page_texts for {len(self.pages)} pages"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    """What an :class:`~cocok_core.ports.protocols.Extractor` returns.

    Args:
        document: The extracted fields.
        field_meta: Per-field metadata keyed by field path, e.g. ``"total_amount"`` or
            ``"line_items[0].qty"``.
        extractor_id: Which extractor/model produced this, e.g. ``"b3-qwen3.5-2b-lora@v1"``.
        raw_output: The model's raw text, kept for debugging and the failure log.
        cost_usd: Money spent on this call (0 for local models).
        latency_ms: Wall-clock time of the call.

    Raises:
        ValueError: If a ``field_meta`` key is not a real field path, or cost/latency < 0.
    """

    document: ExtractedDocument
    field_meta: Mapping[str, FieldMeta]
    extractor_id: str
    raw_output: str = field(default="", repr=False)
    cost_usd: Decimal = Decimal(0)
    latency_ms: int = 0

    def __post_init__(self) -> None:
        unknown = sorted(path for path in self.field_meta if not is_valid_field_path(path))
        if unknown:
            msg = f"field_meta has unknown field paths: {unknown}"
            raise ValueError(msg)
        if self.cost_usd < 0 or self.latency_ms < 0:
            msg = "cost_usd and latency_ms must be >= 0"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class OcrLine:
    """One line of text found by OCR on a page.

    Args:
        text: Recognized text.
        box: ``(x0, y0, x1, y1)``, page-normalized, origin top-left.
        score: Engine confidence in [0, 1] (raw, not calibrated).
    """

    text: str
    box: tuple[float, float, float, float]
    score: float

    def __post_init__(self) -> None:
        check_box(*self.box)
        if not 0 <= self.score <= 1:
            msg = f"score must be in [0, 1], got {self.score}"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class AmountRead:
    """What an amount reader saw in a crop of the total-amount area.

    Args:
        text: Raw recognized characters.
        value: Parsed amount, or ``None`` if the text is not a valid amount.
        seq_prob: Probability of the whole character sequence, in [0, 1].
    """

    text: str
    value: Money | None
    seq_prob: float

    def __post_init__(self) -> None:
        if not 0 <= self.seq_prob <= 1:
            msg = f"seq_prob must be in [0, 1], got {self.seq_prob}"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class StructuredRequest:
    """A request for JSON output that must match ``json_schema``.

    Args:
        prompt_id: Versioned prompt name from ``prompts/`` for tracing, e.g. ``"extract@v3"``.
        system: System instructions.
        user: User message.
        json_schema: The JSON schema the answer must follow.
        schema_name: Short name of that schema (some providers require one).
        images: Page images to attach.
        max_output_tokens: Upper bound on the answer length.
    """

    prompt_id: str
    system: str
    user: str
    json_schema: Mapping[str, object]
    schema_name: str
    images: tuple[PageImage, ...] = ()
    max_output_tokens: int = 2048


@dataclass(frozen=True, slots=True)
class StructuredResponse:
    """A provider's answer to a :class:`StructuredRequest`.

    Args:
        data: Parsed JSON object, not yet validated against our models.
        raw_text: The exact text returned.
        model_id: Exact provider model id, recorded per run (TECH_REFRESH rule).
        input_tokens: Tokens sent.
        output_tokens: Tokens received.
        cost_usd: Cost of this call.
        latency_ms: Wall-clock time of this call.
    """

    data: Mapping[str, object]
    raw_text: str = field(repr=False)
    model_id: str
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal
    latency_ms: int
