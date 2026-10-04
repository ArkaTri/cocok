"""Canonical extraction schema shared by every document type (blueprint §3.2, FS-CM-03).

Three design rules, each with a reason:

1. **Every field except ``doc_type`` is optional.** What is *required* depends on the document
   type and lives in one table, :data:`REQUIRED_FIELDS`. A missing invoice number then becomes a
   ``MISSING_REQUIRED`` review issue (FS-CV-08) instead of a crash that loses the extraction.
2. **Models hold normalized values only.** ``"Rp 1.250.000"`` or ``"2,5"`` never reach these
   classes; the parsers in ``cocok_core.validation`` (CP-03) produce ``Money``/``Decimal``/``date``
   first.
3. **Per-field metadata (confidence, bbox) is NOT inside ``ExtractedDocument``.** This schema is
   sent to LLMs as their output format; if every field carried a confidence, the model would be
   asked to invent one. Our own pipeline computes metadata, and it travels next to the document,
   keyed by field path (``ExtractionResult.field_meta`` in ``cocok_core.ports.types``).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType
from typing import Annotated, Final

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    JsonValue,
    PlainSerializer,
    Strict,
    WithJsonSchema,
    model_validator,
)

from cocok_core.models.money import Money


class DocType(StrEnum):
    """Kinds of document Cocok handles (blueprint §3.1)."""

    PURCHASE_ORDER = "purchase_order"
    INVOICE = "invoice"
    NOTA = "nota"
    KWITANSI = "kwitansi"
    SURAT_JALAN = "surat_jalan"


class BboxSource(StrEnum):
    """Where a field's bounding box came from (ADR-0006)."""

    TEXT_LAYER = "text_layer"
    OCR_ALIGNMENT = "ocr_alignment"
    EXTRACTOR = "extractor"
    NONE = "none"


# ------------------------------------------------------------------ reusable field types
def _blank_to_none(value: object) -> object:
    """Treat ``""`` and whitespace-only strings as missing, so "missing" always means None."""
    if isinstance(value, str) and not value.strip():
        return None
    return value


OptText = Annotated[
    Annotated[str, Field(min_length=1, max_length=500)] | None,
    BeforeValidator(_blank_to_none),
]
"""Optional free text as written: blank becomes ``None``, capped at 500 characters."""

_QTY_RE = re.compile(r"-?\d+(?:\.\d+)?")


def _check_qty_text(value: object) -> object:
    if isinstance(value, str) and not _QTY_RE.fullmatch(value):
        msg = f"quantity must look like '2' or '2.5' (dot decimal, no exponent), got {value!r}"
        raise ValueError(msg)
    return value


Quantity = Annotated[
    Decimal,
    BeforeValidator(_check_qty_text),
    Field(allow_inf_nan=False),
    PlainSerializer(lambda d: format(d, "f"), return_type=str, when_used="json"),
    WithJsonSchema(
        {
            "type": "string",
            "pattern": r"^-?\d+(\.\d+)?$",
            "description": "Exact quantity as a string with a dot decimal, e.g. '2' or '2.5'.",
        }
    ),
]
"""Exact decimal quantity. It travels as a JSON *string*, so no float ever touches it."""

IsoDate = Annotated[date, Strict()]
"""A real ``date`` in Python; an ISO ``YYYY-MM-DD`` string in JSON. Timestamps are rejected."""


def check_box(x0: float, y0: float, x1: float, y1: float) -> None:
    """Validate a page-normalized box (origin top-left).

    The box must satisfy ``0 <= x0 < x1 <= 1`` and ``0 <= y0 < y1 <= 1``.

    Args:
        x0: Left edge.
        y0: Top edge.
        x1: Right edge.
        y1: Bottom edge.

    Raises:
        ValueError: If the box is outside the page, empty, or upside down.

    Example:
        >>> check_box(0.1, 0.2, 0.3, 0.4)
        >>> check_box(0.3, 0.2, 0.1, 0.4)  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        ValueError: box must satisfy 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1, got (0.3, ...)
    """
    if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
        msg = f"box must satisfy 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1, got {(x0, y0, x1, y1)}"
        raise ValueError(msg)


_BBoxTuple = tuple[int, float, float, float, float]


def _check_bbox(value: _BBoxTuple) -> _BBoxTuple:
    page, x0, y0, x1, y1 = value
    if page < 0:
        msg = f"bbox page must be >= 0, got {page}"
        raise ValueError(msg)
    check_box(x0, y0, x1, y1)
    return value


BBox = Annotated[_BBoxTuple, AfterValidator(_check_bbox)]
"""``(page, x0, y0, x1, y1)``: 0-based page, page-normalized coordinates, origin top-left."""

_MODEL_CONFIG = ConfigDict(frozen=True, extra="forbid")


# ------------------------------------------------------------------ models
class LineItem(BaseModel):
    """One row of goods or services on a document."""

    model_config = _MODEL_CONFIG

    description: OptText = Field(default=None, description="Item name exactly as written.")
    qty: Quantity | None = None
    unit: OptText = Field(default=None, description="Unit as written, e.g. 'pcs', 'kg', 'sak'.")
    unit_price: Money | None = None
    line_total: Money | None = None


def _none_to_empty(value: object) -> object:
    return () if value is None else value


class ExtractedDocument(BaseModel):
    """Fields read from one business document. Unknown or unreadable fields are null."""

    model_config = _MODEL_CONFIG

    doc_type: DocType
    vendor_name: OptText = Field(default=None, description="Seller / issuer name as written.")
    vendor_npwp: Annotated[str, Field(pattern=r"^\d{16}$")] | None = Field(
        default=None, description="Vendor tax ID, normalized to exactly 16 digits."
    )
    vendor_nitku: Annotated[str, Field(pattern=r"^\d{22}$")] | None = Field(
        default=None, description="Vendor place-of-business ID: 16-digit NPWP + 6-digit code."
    )
    doc_number: OptText = Field(default=None, description="Document number as written.")
    doc_date: IsoDate | None = Field(default=None, description="Document date, YYYY-MM-DD.")
    po_reference: OptText = Field(default=None, description="Purchase-order number referenced.")
    payer_name: OptText = Field(
        default=None, description="Kwitansi 'Sudah terima dari' (received from)."
    )
    line_items: Annotated[tuple[LineItem, ...], BeforeValidator(_none_to_empty)] = ()
    subtotal: Money | None = None
    tax_amount: Money | None = None
    total_amount: Money | None = None
    amount_in_words: OptText = Field(
        default=None, description="Amount in words (terbilang), raw text as written."
    )
    received_by: OptText = Field(default=None, description="Name of the person who received.")


class FieldMeta(BaseModel):
    """What the pipeline knows about one extracted field: raw text, confidence, location."""

    model_config = _MODEL_CONFIG

    value_raw: str | None = None
    value_normalized: JsonValue = None
    confidence: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    bbox: BBox | None = None
    bbox_source: BboxSource = BboxSource.NONE
    signals: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _bbox_and_source_agree(self) -> FieldMeta:
        has_box = self.bbox is not None
        says_none = self.bbox_source is BboxSource.NONE
        if has_box == says_none:
            msg = "bbox and bbox_source disagree: a box needs a source; 'none' needs no box"
            raise ValueError(msg)
        return self


# ------------------------------------------------------------------ requiredness (§3.2 table)
REQUIRED_FIELDS: Final[Mapping[DocType, frozenset[str]]] = MappingProxyType(
    {
        DocType.INVOICE: frozenset(
            {"vendor_name", "doc_number", "doc_date", "total_amount", "line_items"}
        ),
        DocType.NOTA: frozenset({"vendor_name", "doc_date", "total_amount", "line_items"}),
        DocType.KWITANSI: frozenset({"payer_name", "total_amount", "amount_in_words", "doc_date"}),
        DocType.SURAT_JALAN: frozenset({"vendor_name", "doc_number", "doc_date", "line_items"}),
        DocType.PURCHASE_ORDER: frozenset(),  # structured input, never extracted
    }
)
"""Fields that must be present per document type. ``line_items`` means "at least one item".

Example:
    >>> sorted(REQUIRED_FIELDS[DocType.KWITANSI])
    ['amount_in_words', 'doc_date', 'payer_name', 'total_amount']
"""

REQUIRED_LINE_ITEM_FIELDS: Final[Mapping[DocType, frozenset[str]]] = MappingProxyType(
    {
        DocType.INVOICE: frozenset(),
        DocType.NOTA: frozenset(),
        DocType.KWITANSI: frozenset(),
        DocType.SURAT_JALAN: frozenset({"description", "qty"}),
        DocType.PURCHASE_ORDER: frozenset(),
    }
)
"""Fields every line item must have, per type (§3.2: a surat jalan needs qty + description)."""

# ------------------------------------------------------------------ field paths for FieldMeta
_FIELD_PATH_RE = re.compile(r"(?P<field>[a-z_]+)(?:\[(?P<index>\d+)\]\.(?P<sub>[a-z_]+))?")


def is_valid_field_path(path: str) -> bool:
    """Tell whether ``path`` names a real field of the schema.

    Valid forms are a top-level field (``"total_amount"``) or a line-item field
    (``"line_items[0].unit_price"``).

    Args:
        path: Field path used as a key in ``ExtractionResult.field_meta``.

    Returns:
        ``True`` if the path points at an existing field of ``ExtractedDocument``/``LineItem``.

    Example:
        >>> is_valid_field_path("line_items[2].qty")
        True
        >>> is_valid_field_path("total"), is_valid_field_path("vendor_name[0].x")
        (False, False)
    """
    match = _FIELD_PATH_RE.fullmatch(path)
    if match is None:
        return False
    field, sub = match["field"], match["sub"]
    if field not in ExtractedDocument.model_fields:
        return False
    if sub is None:
        return True
    return field == "line_items" and sub in LineItem.model_fields
