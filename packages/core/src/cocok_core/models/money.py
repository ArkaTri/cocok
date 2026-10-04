"""Money value object: whole rupiah stored as ``int``, never ``float`` (FS-CM-01).

Why ``int`` and not ``float`` or ``Decimal``:

* Rupiah has no sub-unit in practice, so whole numbers are exact and cheap.
* ``float`` cannot store most decimal amounts exactly (``0.1 + 0.2 != 0.3``). One silent
  rounding error in a reconciliation system is a wrong payment.
* Multiplying by a fractional quantity is the only operation that needs rounding, so it is the
  only operation that asks for a rounding mode: :meth:`Money.times`.

Negative amounts are allowed on purpose: ``invoice_total - po_total`` must be able to say
"Rp 50.000 short". Rules such as "a total must be positive" belong to the validators (CP-04),
not to the value type.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import (
    ROUND_CEILING,
    ROUND_FLOOR,
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    Decimal,
    localcontext,
)
from typing import Annotated, ClassVar, Final, Literal, cast

from pydantic import ConfigDict, Strict

Rounding = Literal["half_up", "half_even", "floor", "ceiling"]
"""Rounding modes for :meth:`Money.times`. The tax rules in CP-04 pick one per rule."""

_DECIMAL_ROUNDING: Final[dict[str, str]] = {
    "half_up": ROUND_HALF_UP,
    "half_even": ROUND_HALF_EVEN,
    "floor": ROUND_FLOOR,
    "ceiling": ROUND_CEILING,
}


@dataclass(frozen=True, slots=True, order=True)
class Money:
    """An amount of Indonesian rupiah in whole units.

    Args:
        amount_idr: Whole rupiah. Must be exactly ``int``: ``bool``, ``float``, ``Decimal`` and
            ``str`` are rejected so no caller can smuggle in a fractional or unparsed value.

    Raises:
        TypeError: If ``amount_idr`` is not exactly an ``int``.

    Example:
        >>> Money(1_250_000) + Money(50_000)
        Money(amount_idr=1300000)
        >>> Money(10_000).times(Decimal("2.5"), "half_up")
        Money(amount_idr=25000)
        >>> sum([Money(1), Money(2)], Money.zero())
        Money(amount_idr=3)
        >>> Money(1.5)
        Traceback (most recent call last):
        ...
        TypeError: Money.amount_idr must be int, got float
    """

    # Read by Pydantic when Money sits inside a model: no unknown keys, and a short schema
    # description (the schema goes to LLMs later, so the long docstring must not leak into it).
    __pydantic_config__: ClassVar[ConfigDict] = ConfigDict(
        extra="forbid",
        json_schema_extra={"description": "Whole Indonesian rupiah (integer, never a float)."},
    )

    # Strict() stops Pydantic from coercing 1250000.0 or "1250000" inside a model.
    amount_idr: Annotated[int, Strict()]

    def __post_init__(self) -> None:
        # `type(x) is int` (not isinstance) also rejects bool, which is a subclass of int.
        if type(self.amount_idr) is not int:
            msg = f"Money.amount_idr must be int, got {type(self.amount_idr).__name__}"
            raise TypeError(msg)

    @classmethod
    def zero(cls) -> Money:
        """Return ``Money(0)``; use it as the start value of ``sum()``.

        Returns:
            A zero amount.
        """
        return cls(0)

    def __add__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self.amount_idr + other.amount_idr)

    def __sub__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self.amount_idr - other.amount_idr)

    def __neg__(self) -> Money:
        return Money(-self.amount_idr)

    def times(self, qty: Decimal, rounding: Rounding) -> Money:
        """Multiply by a quantity and round to whole rupiah with an explicit mode.

        Args:
            qty: Exact quantity, e.g. ``Decimal("2.5")`` kg. ``float`` is rejected.
            rounding: ``"half_up"``, ``"half_even"``, ``"floor"`` or ``"ceiling"``.

        Returns:
            A new ``Money``; ``self`` is unchanged.

        Raises:
            TypeError: If ``qty`` is not a ``Decimal``.
            ValueError: If ``qty`` is NaN/Infinity or ``rounding`` is unknown.

        Example:
            >>> Money(1_001).times(Decimal("0.5"), "half_up")
            Money(amount_idr=501)
            >>> Money(1_001).times(Decimal("0.5"), "floor")
            Money(amount_idr=500)
        """
        # cast(): mypy trusts the annotation, but untyped callers can still pass a float.
        if not isinstance(cast("object", qty), Decimal):
            msg = f"qty must be Decimal, got {type(qty).__name__}"
            raise TypeError(msg)
        if not qty.is_finite():
            msg = f"qty must be finite, got {qty}"
            raise ValueError(msg)
        mode = _DECIMAL_ROUNDING.get(rounding)
        if mode is None:
            msg = f"unknown rounding mode {rounding!r}; use one of {sorted(_DECIMAL_ROUNDING)}"
            raise ValueError(msg)
        # Enough precision that the product is exact before the single, explicit rounding.
        with localcontext() as ctx:
            ctx.prec = 60
            product = Decimal(self.amount_idr) * qty
            return Money(int(product.quantize(Decimal(1), rounding=mode)))
