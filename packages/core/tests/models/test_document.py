"""CP-02 · FS-CM-03 ExtractedDocument, LineItem, FieldMeta, REQUIRED_FIELDS."""

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError as PydanticValidationError

from cocok_core.models.document import (
    REQUIRED_FIELDS,
    REQUIRED_LINE_ITEM_FIELDS,
    BboxSource,
    DocType,
    ExtractedDocument,
    FieldMeta,
    LineItem,
    is_valid_field_path,
)
from cocok_core.models.money import Money

pytestmark = pytest.mark.cp02

NOTA_JSON = """
{
  "doc_type": "nota",
  "vendor_name": "Toko Bangunan Sumber Rejeki",
  "doc_date": "2026-10-01",
  "line_items": [
    {"description": "Semen 50kg", "qty": "2.5", "unit": "sak",
     "unit_price": {"amount_idr": 65000}, "line_total": {"amount_idr": 162500}}
  ],
  "total_amount": {"amount_idr": 162500}
}
"""


# --------------------------------------------------------------------------- happy path
def test_only_doc_type_is_required() -> None:
    doc = ExtractedDocument(doc_type=DocType.INVOICE)
    assert doc.vendor_name is None
    assert doc.line_items == ()
    assert doc.total_amount is None


def test_parses_a_realistic_nota() -> None:
    doc = ExtractedDocument.model_validate_json(NOTA_JSON)
    assert doc.doc_type is DocType.NOTA
    assert doc.doc_date == date(2026, 10, 1)
    assert doc.line_items[0].qty == Decimal("2.5")
    assert doc.total_amount == Money(162_500)


def test_json_round_trip_keeps_qty_as_string() -> None:
    doc = ExtractedDocument.model_validate_json(NOTA_JSON)
    dumped = doc.model_dump_json()
    assert '"qty":"2.5"' in dumped
    assert ExtractedDocument.model_validate_json(dumped) == doc


def test_models_are_frozen() -> None:
    doc = ExtractedDocument(doc_type=DocType.NOTA)
    with pytest.raises(PydanticValidationError):
        doc.vendor_name = "x"  # type: ignore[misc]


@pytest.mark.parametrize("blank", ["", "   ", "\n"])
def test_blank_text_becomes_none(blank: str) -> None:
    doc = ExtractedDocument.model_validate({"doc_type": "nota", "vendor_name": blank})
    assert doc.vendor_name is None


def test_null_line_items_become_empty() -> None:
    doc = ExtractedDocument.model_validate({"doc_type": "invoice", "line_items": None})
    assert doc.line_items == ()


# --------------------------------------------------------------------------- rejections
@pytest.mark.parametrize(
    ("patch", "error_type"),
    [
        ({"doc_type": "bon"}, "enum"),
        ({"surprise": 1}, "extra_forbidden"),
        ({"vendor_npwp": "01.234.567.8-901.000"}, "string_pattern_mismatch"),
        ({"vendor_npwp": "123456789012345"}, "string_pattern_mismatch"),  # 15 digits: legacy
        ({"vendor_nitku": "1234567890123456"}, "string_pattern_mismatch"),  # NPWP, not NITKU
        ({"doc_date": 1696000000}, "date_type"),  # timestamps are not dates
        ({"doc_date": 1696118400}, "date_type"),  # not even an exact-midnight timestamp
        ({"doc_date": "01/10/2026"}, "date_type"),  # D/M/Y parsing is the job of CP-03
        ({"total_amount": {"amount_idr": 1.5}}, "int_type"),
        ({"vendor_name": "x" * 501}, "string_too_long"),
        ({"line_items": [{"qty": "2,5"}]}, "value_error"),
        ({"line_items": [{"qty": "1e3"}]}, "value_error"),
        ({"line_items": [{"qty": "NaN"}]}, "value_error"),
        ({"line_items": [{"price": 1}]}, "extra_forbidden"),
    ],
)
def test_rejects_bad_values(patch: dict[str, Any], error_type: str) -> None:
    payload = {"doc_type": "nota", **patch}
    with pytest.raises(PydanticValidationError) as exc:
        ExtractedDocument.model_validate(payload)
    assert exc.value.errors()[0]["type"] == error_type


def test_strict_false_would_disable_the_protection() -> None:
    # Lesson from CP-02: passing strict=False overrides the field-level Strict() markers.
    # Never call model_validate(..., strict=False) on these models.
    payload = {"doc_type": "nota", "total_amount": {"amount_idr": 5.0}}
    with pytest.raises(PydanticValidationError):
        ExtractedDocument.model_validate(payload)
    loose = ExtractedDocument.model_validate(payload, strict=False)
    assert loose.total_amount == Money(5)


@pytest.mark.parametrize("bad_date", ["1696000000", '"01/10/2026"', '"2026-13-01"'])
def test_rejects_bad_dates_from_json_too(bad_date: str) -> None:
    with pytest.raises(PydanticValidationError):
        ExtractedDocument.model_validate_json(f'{{"doc_type": "nota", "doc_date": {bad_date}}}')


# --------------------------------------------------------------------------- FieldMeta
def test_field_meta_defaults() -> None:
    meta = FieldMeta()
    assert meta.bbox is None
    assert meta.bbox_source is BboxSource.NONE
    assert meta.signals == {}


def test_field_meta_with_box() -> None:
    meta = FieldMeta(
        value_raw="Rp 162.500",
        value_normalized={"amount_idr": 162500},
        confidence=0.97,
        bbox=(0, 0.6, 0.8, 0.9, 0.85),
        bbox_source=BboxSource.OCR_ALIGNMENT,
        signals={"ocr_score": 0.93, "arithmetic_ok": 1.0},
    )
    assert meta.bbox == (0, 0.6, 0.8, 0.9, 0.85)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"bbox": (0, 0.1, 0.1, 0.2, 0.2)},  # box without source
        {"bbox_source": "extractor"},  # source without box
        {"bbox": (-1, 0.1, 0.1, 0.2, 0.2), "bbox_source": "extractor"},  # negative page
        {"bbox": (0, 0.5, 0.1, 0.2, 0.2), "bbox_source": "extractor"},  # x0 > x1
        {"bbox": (0, 0.1, 0.1, 0.1, 0.2), "bbox_source": "extractor"},  # zero width
        {"bbox": (0, 0.1, 0.1, 1.2, 0.2), "bbox_source": "extractor"},  # off the page
        {"bbox": (0, 0.1, 0.1, 0.2), "bbox_source": "extractor"},  # 4 numbers, not 5
        {"confidence": 1.01},
        {"confidence": -0.1},
        {"confidence": float("nan")},
    ],
)
def test_field_meta_rejects(kwargs: dict[str, Any]) -> None:
    with pytest.raises(PydanticValidationError):
        FieldMeta(**kwargs)


# --------------------------------------------------------------------------- REQUIRED_FIELDS
def test_every_doc_type_has_requirements() -> None:
    assert set(REQUIRED_FIELDS) == set(DocType)
    assert set(REQUIRED_LINE_ITEM_FIELDS) == set(DocType)


def test_required_names_are_real_fields() -> None:
    doc_fields = set(ExtractedDocument.model_fields) - {"doc_type"}
    item_fields = set(LineItem.model_fields)
    for doc_type in DocType:
        assert REQUIRED_FIELDS[doc_type] <= doc_fields, doc_type
        assert REQUIRED_LINE_ITEM_FIELDS[doc_type] <= item_fields, doc_type


def test_required_fields_match_blueprint_table() -> None:
    assert REQUIRED_FIELDS[DocType.INVOICE] == {
        "vendor_name",
        "doc_number",
        "doc_date",
        "total_amount",
        "line_items",
    }
    assert REQUIRED_FIELDS[DocType.NOTA] == {
        "vendor_name",
        "doc_date",
        "total_amount",
        "line_items",
    }
    assert REQUIRED_FIELDS[DocType.KWITANSI] == {
        "payer_name",
        "total_amount",
        "amount_in_words",
        "doc_date",
    }
    assert REQUIRED_FIELDS[DocType.SURAT_JALAN] == {
        "vendor_name",
        "doc_number",
        "doc_date",
        "line_items",
    }
    assert REQUIRED_FIELDS[DocType.PURCHASE_ORDER] == frozenset()
    assert REQUIRED_LINE_ITEM_FIELDS[DocType.SURAT_JALAN] == {"description", "qty"}


def test_required_tables_are_read_only() -> None:
    with pytest.raises(TypeError):
        REQUIRED_FIELDS[DocType.NOTA] = frozenset()  # type: ignore[index]


# --------------------------------------------------------------------------- field paths
@pytest.mark.parametrize(
    ("path", "ok"),
    [
        ("total_amount", True),
        ("doc_type", True),
        ("line_items", True),
        ("line_items[0].unit_price", True),
        ("line_items[12].qty", True),
        ("total", False),
        ("line_items[0].price", False),
        ("vendor_name[0].x", False),
        ("line_items[-1].qty", False),
        ("line_items.qty", False),
        ("Total_Amount", False),
        ("", False),
    ],
)
def test_field_paths(path: str, ok: bool) -> None:
    assert is_valid_field_path(path) is ok
