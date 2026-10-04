"""CP-02 · FS-CM-01 Money value object."""

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from cocok_core.models.money import Money

pytestmark = pytest.mark.cp02

amounts = st.integers(min_value=-(10**15), max_value=10**15)
money = amounts.map(Money)


class _Holder(BaseModel):
    m: Money


# --------------------------------------------------------------------------- construction
@pytest.mark.parametrize("bad", [True, 1.0, 1.5, Decimal(1), "1000", None])
def test_rejects_anything_but_int(bad: object) -> None:
    with pytest.raises(TypeError, match="must be int"):
        Money(bad)  # type: ignore[arg-type]


def test_is_immutable_and_hashable() -> None:
    m = Money(5)
    with pytest.raises(FrozenInstanceError):
        m.amount_idr = 6  # type: ignore[misc]
    assert {Money(5), Money(5)} == {Money(5)}


def test_negative_amounts_are_allowed() -> None:
    assert Money(100) - Money(150) == Money(-50)
    assert -Money(7) == Money(-7)


# --------------------------------------------------------------------------- arithmetic
def test_spec_examples() -> None:
    assert Money(1_250_000) + Money(50_000) == Money(1_300_000)
    assert Money(10_000).times(Decimal("2.5"), "half_up") == Money(25_000)


def test_sum_needs_zero_start() -> None:
    assert sum([Money(1), Money(2), Money(3)], Money.zero()) == Money(6)
    with pytest.raises(TypeError):
        sum([Money(1)])  # type: ignore[list-item]  # 0 + Money is deliberately unsupported


def test_ordering() -> None:
    assert Money(1) < Money(2) <= Money(2)
    assert max(Money(3), Money(9), Money(4)) == Money(9)


def test_cannot_mix_with_plain_numbers() -> None:
    with pytest.raises(TypeError):
        Money(1) + 1  # type: ignore[operator]


@pytest.mark.parametrize(
    ("amount", "qty", "rounding", "expected"),
    [
        (1_001, "0.5", "half_up", 501),  # 500.5 -> 501
        (1_001, "0.5", "half_even", 500),  # 500.5 -> 500 (banker's rounding)
        (1_003, "0.5", "half_even", 502),  # 501.5 -> 502
        (1_001, "0.5", "floor", 500),
        (1_001, "0.5", "ceiling", 501),
        (-1_001, "0.5", "floor", -501),  # floor goes towards minus infinity
        (65_000, "2.5", "half_up", 162_500),
        (7, "0", "half_up", 0),
    ],
)
def test_times_rounding_modes(amount: int, qty: str, rounding: str, expected: int) -> None:
    assert Money(amount).times(Decimal(qty), rounding) == Money(expected)  # type: ignore[arg-type]


def test_times_rejects_float_nan_and_unknown_mode() -> None:
    with pytest.raises(TypeError, match="Decimal"):
        Money(10).times(2.5, "half_up")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="finite"):
        Money(10).times(Decimal("NaN"), "half_up")
    with pytest.raises(ValueError, match="rounding"):
        Money(10).times(Decimal(1), "round_up")  # type: ignore[arg-type]


def test_times_is_exact_for_huge_amounts() -> None:
    # 28-digit default Decimal precision would round here; Money.times raises it to 60.
    big = 10**25 + 1
    assert Money(big).times(Decimal("1.5"), "half_up") == Money(15 * 10**24 + 2)


@given(money, money, money)
def test_addition_is_associative(a: Money, b: Money, c: Money) -> None:
    assert (a + b) + c == a + (b + c)


@given(money, money)
def test_addition_is_commutative_and_sub_undoes_add(a: Money, b: Money) -> None:
    assert a + b == b + a
    assert (a + b) - b == a


@given(money)
def test_times_one_is_identity(a: Money) -> None:
    assert a.times(Decimal(1), "half_up") == a


# --------------------------------------------------------------------------- inside Pydantic models
def test_pydantic_accepts_real_money_and_dicts() -> None:
    assert _Holder(m=Money(3)).m == Money(3)
    assert _Holder.model_validate({"m": {"amount_idr": 3}}).m == Money(3)
    assert _Holder.model_validate_json('{"m": {"amount_idr": 3}}').m == Money(3)


@pytest.mark.parametrize(
    "raw",
    [
        '{"m": {"amount_idr": 3.0}}',
        '{"m": {"amount_idr": "3"}}',
        '{"m": {"amount_idr": true}}',
        '{"m": {"amount_idr": 3, "currency": "IDR"}}',
        '{"m": 3}',
    ],
)
def test_pydantic_never_coerces(raw: str) -> None:
    with pytest.raises(PydanticValidationError):
        _Holder.model_validate_json(raw)


def test_json_round_trip() -> None:
    h = _Holder(m=Money(1_250_000))
    assert h.model_dump_json() == '{"m":{"amount_idr":1250000}}'
    assert _Holder.model_validate_json(h.model_dump_json()) == h
