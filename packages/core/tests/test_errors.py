"""CP-02 · FS-CM-04 error hierarchy."""

import inspect

import pydantic
import pytest

from cocok_core import errors
from cocok_core.errors import (
    DomainError,
    DomainValidationError,
    ExternalTimeout,
    InvalidTransition,
    MoneyParseError,
    PermanentExternalError,
    ProviderUnavailable,
    RateLimited,
    RetryableError,
)

pytestmark = pytest.mark.cp02

ALL_ERRORS = [
    obj
    for _, obj in inspect.getmembers(errors, inspect.isclass)
    if issubclass(obj, DomainError) and obj.__module__ == errors.__name__
]


def test_hierarchy_is_complete() -> None:
    names = {cls.__name__ for cls in ALL_ERRORS}
    assert names == {
        "DomainError",
        "DomainValidationError",
        "MoneyParseError",
        "DateParseError",
        "NpwpError",
        "TerbilangError",
        "RulesError",
        "InvalidTransition",
        "InvalidModelOutput",
        "LicenseViolation",
        "CalibratorMismatch",
        "RetryableError",
        "ExternalTimeout",
        "RateLimited",
        "ProviderUnavailable",
        "PermanentExternalError",
    }


@pytest.mark.parametrize("cls", ALL_ERRORS, ids=lambda c: c.__name__)
def test_each_class_has_its_own_valid_code(cls: type[DomainError]) -> None:
    err = cls()
    assert err.code == cls.default_code
    assert err.message == cls.default_code
    assert str(err) == f"[{cls.default_code}] {cls.default_code}"


def test_default_codes_are_unique() -> None:
    codes = [cls.default_code for cls in ALL_ERRORS]
    assert len(codes) == len(set(codes))


@pytest.mark.parametrize("bad", ["lower", "Mixed_Case", "TRAILING_", "_LEADING", "SPACE CODE", ""])
def test_rejects_non_upper_snake_codes(bad: str) -> None:
    with pytest.raises(ValueError, match="UPPER_SNAKE"):
        DomainError("x", code=bad)


def test_context_is_kept_and_read_only() -> None:
    err = MoneyParseError("cannot parse", raw="1.25")
    assert err.context["raw"] == "1.25"
    with pytest.raises(TypeError):
        err.context["raw"] = "x"  # type: ignore[index]


def test_to_dict_is_json_friendly() -> None:
    err = RateLimited("slow down", retry_after_s=30, provider=object())
    data = err.to_dict()
    assert data["code"] == "RATE_LIMITED"
    assert data["message"] == "slow down"
    ctx = data["context"]
    assert isinstance(ctx, dict)
    assert ctx["retry_after_s"] == 30
    assert isinstance(ctx["provider"], str)


def test_only_temporary_failures_are_retryable() -> None:
    for cls in (ExternalTimeout, RateLimited, ProviderUnavailable):
        assert issubclass(cls, RetryableError)
    assert not issubclass(PermanentExternalError, RetryableError)
    assert not issubclass(InvalidTransition, RetryableError)
    assert not issubclass(DomainValidationError, RetryableError)


def test_not_confused_with_pydantic() -> None:
    assert not issubclass(DomainValidationError, pydantic.ValidationError)
    assert DomainValidationError.__name__ != pydantic.ValidationError.__name__


def test_code_can_be_overridden_per_raise() -> None:
    err = InvalidTransition("limit", code="RETRY_LIMIT_REACHED")
    assert isinstance(err, InvalidTransition)
    assert err.code == "RETRY_LIMIT_REACHED"


def test_errors_are_real_exceptions() -> None:
    with pytest.raises(DomainError):
        raise MoneyParseError("boom")
