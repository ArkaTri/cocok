"""CP-02 · FS-CM-05 ports: fakes satisfy every Protocol, and ports speak domain types only."""

import asyncio
import inspect
import typing
from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from cocok_core import ports
from cocok_core.models.document import DocType, ExtractedDocument, FieldMeta
from cocok_core.models.money import Money
from cocok_core.ports import (
    AmountRead,
    AmountReader,
    Clock,
    DocumentInput,
    ExtractionResult,
    Extractor,
    IdGenerator,
    JobQueue,
    LLMClient,
    OcrEngine,
    OcrLine,
    PageImage,
    Storage,
    StructuredRequest,
    StructuredResponse,
    Transaction,
)

pytestmark = pytest.mark.cp02

PNG = PageImage(data=b"\x89PNG fake", mime="image/png", width=100, height=200)
DOC_ID = UUID("01920000-0000-7000-8000-000000000001")


# ------------------------------------------------------------------ fakes (reused in later CPs)
class FakeExtractor:
    async def extract(self, doc: DocumentInput) -> ExtractionResult:
        return ExtractionResult(
            document=ExtractedDocument(doc_type=doc.doc_type_hint or DocType.NOTA),
            field_meta={"doc_type": FieldMeta(confidence=1.0)},
            extractor_id="fake@v0",
        )


class FakeAmountReader:
    def read(self, crop: PageImage) -> AmountRead:
        return AmountRead(text="162500", value=Money(162_500), seq_prob=0.9)


class FakeOcr:
    def lines(self, page: PageImage) -> list[OcrLine]:
        return [OcrLine(text="TOTAL 162.500", box=(0.1, 0.8, 0.9, 0.85), score=0.95)]


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = data

    async def get(self, key: str) -> bytes:
        return self.objects[key]

    async def presign_get(self, key: str, ttl_s: int) -> str:
        return f"https://storage.invalid/{key}?ttl={ttl_s}"


class FakeLLM:
    async def structured(self, req: StructuredRequest) -> StructuredResponse:
        return StructuredResponse(
            data={"doc_type": "nota"},
            raw_text='{"doc_type": "nota"}',
            model_id="fake-model",
            input_tokens=10,
            output_tokens=5,
            cost_usd=Decimal(0),
            latency_ms=1,
        )


class FakeQueue:
    async def enqueue_in_tx(
        self, tx: Transaction, task: str, args: Mapping[str, object], lock: str
    ) -> str | None:
        return f"job:{task}:{lock}"


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 10, 1, 9, 0, tzinfo=UTC)


class SequentialIds:
    def __init__(self) -> None:
        self.n = 0

    def new(self) -> UUID:
        self.n += 1
        return UUID(int=self.n)


# The cp02 gate runs mypy on this file: a fake with a wrong signature fails the gate.
_extractor: Extractor = FakeExtractor()
_reader: AmountReader = FakeAmountReader()
_ocr: OcrEngine = FakeOcr()
_storage: Storage = FakeStorage()
_llm: LLMClient = FakeLLM()
_queue: JobQueue = FakeQueue()
_clock: Clock = FixedClock()
_ids: IdGenerator = SequentialIds()

PAIRS: list[tuple[type, object]] = [
    (Extractor, _extractor),
    (AmountReader, _reader),
    (OcrEngine, _ocr),
    (Storage, _storage),
    (LLMClient, _llm),
    (JobQueue, _queue),
    (Clock, _clock),
    (IdGenerator, _ids),
]


@pytest.mark.parametrize(("port", "fake"), PAIRS, ids=lambda x: getattr(x, "__name__", ""))
def test_fakes_satisfy_ports_at_runtime(port: type, fake: object) -> None:
    assert isinstance(fake, port)


def test_an_unrelated_object_is_not_a_port() -> None:
    assert not isinstance(object(), Extractor)
    assert not isinstance(FixedClock(), Storage)


def test_fakes_work_end_to_end() -> None:
    doc = DocumentInput(document_id=DOC_ID, pages=(PNG,), doc_type_hint=DocType.INVOICE)
    result = asyncio.run(_extractor.extract(doc))
    assert result.document.doc_type is DocType.INVOICE
    assert _clock.now().tzinfo is UTC

    async def storage_round_trip() -> bytes:
        await _storage.put("a/b.png", b"x", "image/png")
        return await _storage.get("a/b.png")

    assert asyncio.run(storage_round_trip()) == b"x"


# --------------------------------------------------------------------------- domain types only
_ALLOWED_MODULE_PREFIXES = (
    "cocok_core",
    "builtins",
    "typing",
    "collections.abc",
    "datetime",
    "decimal",
    "uuid",
    "types",
)


def _leaf_types(tp: object) -> list[object]:
    args = typing.get_args(tp)
    if not args:
        return [tp]
    leaves = [typing.get_origin(tp)]
    for arg in args:
        leaves.extend(_leaf_types(arg))
    return leaves


PORT_CLASSES = [
    Extractor,
    AmountReader,
    OcrEngine,
    Storage,
    LLMClient,
    JobQueue,
    Clock,
    IdGenerator,
]


@pytest.mark.parametrize("port", PORT_CLASSES, ids=lambda p: p.__name__)
def test_ports_speak_domain_types_only(port: type) -> None:
    methods = [
        m for name, m in inspect.getmembers(port, inspect.isfunction) if not name.startswith("_")
    ]
    assert methods, f"{port.__name__} has no methods"
    for method in methods:
        hints = typing.get_type_hints(method, vars(ports.protocols))
        for annotation in hints.values():
            for leaf in _leaf_types(annotation):
                module = getattr(leaf, "__module__", "builtins")
                assert module.startswith(_ALLOWED_MODULE_PREFIXES), (port.__name__, leaf)


# --------------------------------------------------------------------------- port data types
@pytest.mark.parametrize(
    "kwargs",
    [
        {"data": b"", "mime": "image/png", "width": 1, "height": 1},
        {"data": b"x", "mime": "image/gif", "width": 1, "height": 1},
        {"data": b"x", "mime": "image/png", "width": 0, "height": 1},
        {"data": b"x", "mime": "image/png", "width": 1, "height": 1, "page": -1},
    ],
)
def test_page_image_rejects(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        PageImage(**kwargs)  # type: ignore[arg-type]


def test_page_image_repr_hides_bytes() -> None:
    assert "PNG fake" not in repr(PNG)


def test_document_input_rules() -> None:
    with pytest.raises(ValueError, match="at least one page"):
        DocumentInput(document_id=DOC_ID, pages=())
    with pytest.raises(ValueError, match="page_texts"):
        DocumentInput(document_id=DOC_ID, pages=(PNG,), page_texts=("a", "b"))
    ok = DocumentInput(document_id=DOC_ID, pages=(PNG, PNG), page_texts=("a", "b"))
    assert len(ok.pages) == 2


def test_extraction_result_checks_field_paths() -> None:
    doc = ExtractedDocument(doc_type=DocType.NOTA)
    ExtractionResult(
        document=doc,
        field_meta={"total_amount": FieldMeta(), "line_items[0].qty": FieldMeta()},
        extractor_id="x",
    )
    with pytest.raises(ValueError, match="unknown field paths"):
        ExtractionResult(document=doc, field_meta={"totl": FieldMeta()}, extractor_id="x")
    with pytest.raises(ValueError, match=">= 0"):
        ExtractionResult(document=doc, field_meta={}, extractor_id="x", latency_ms=-1)


@pytest.mark.parametrize(
    ("box", "score"),
    [((0.5, 0.1, 0.4, 0.2), 0.5), ((0.1, 0.1, 0.4, 0.2), 1.5)],
)
def test_ocr_line_rejects(box: tuple[float, float, float, float], score: float) -> None:
    with pytest.raises(ValueError):
        OcrLine(text="x", box=box, score=score)


def test_amount_read_probability_range() -> None:
    with pytest.raises(ValueError):
        AmountRead(text="1", value=None, seq_prob=-0.1)
