"""Domain error hierarchy with stable, machine-readable codes (FS-CM-04).

Every error carries an UPPER_SNAKE ``code`` that API clients, logs and tests can rely on even
when the human-readable message changes. Catch by class inside Python; compare by ``code``
everywhere else.

Hierarchy::

    DomainError
    ├── DomainValidationError     bad input value (parsers, validators, rules)
    │   ├── MoneyParseError
    │   ├── DateParseError
    │   ├── NpwpError
    │   ├── TerbilangError
    │   └── RulesError
    ├── InvalidTransition         document state machine (FS-CM-02)
    ├── InvalidModelOutput        model output does not match the schema (FS-AD-01)
    ├── LicenseViolation          dataset/model licence rule broken
    ├── CalibratorMismatch        calibrator artefact does not match its input signals
    ├── RetryableError            the ONLY base the job queue retries on
    │   ├── ExternalTimeout
    │   ├── RateLimited
    │   └── ProviderUnavailable
    └── PermanentExternalError    external call failed; retrying will not help

``DomainValidationError`` is deliberately NOT called ``ValidationError``: Pydantic owns that
name, and two different classes with the same name in one ``except`` clause is a classic
source of silent bugs. Names without an ``Error`` suffix (``InvalidTransition``, ``RateLimited``)
read better at the raise site and are allowed by a ruff per-file ignore (N818).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from types import MappingProxyType
from typing import ClassVar

_CODE_RE = re.compile(r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*")


class DomainError(Exception):
    """Base class for every error raised by Cocok domain code.

    Args:
        message: Human-readable explanation. Defaults to the code itself.
        code: Stable UPPER_SNAKE identifier. Defaults to the class's ``default_code``.
        **context: Extra facts for logs and API responses (e.g. ``raw="1.25"``), stored
            read-only.

    Raises:
        ValueError: If ``code`` is not UPPER_SNAKE (a programming error, not a domain error).

    Example:
        >>> err = DomainError("something broke", code="EXAMPLE_FAILURE", field="total_amount")
        >>> err.code, err.context["field"]
        ('EXAMPLE_FAILURE', 'total_amount')
        >>> str(err)
        '[EXAMPLE_FAILURE] something broke'
    """

    default_code: ClassVar[str] = "DOMAIN_ERROR"

    code: str
    message: str
    context: Mapping[str, object]

    def __init__(self, message: str = "", *, code: str | None = None, **context: object) -> None:
        resolved = code if code is not None else self.default_code
        if not _CODE_RE.fullmatch(resolved):
            msg = f"error code must be UPPER_SNAKE, got {resolved!r}"
            raise ValueError(msg)
        self.code = resolved
        self.message = message or resolved
        self.context = MappingProxyType(dict(context))
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly view, used later by the API's error responses.

        Returns:
            ``{"code": ..., "message": ..., "context": {...}}``. Context values that are not
            plain JSON scalars are converted with ``str``.
        """
        scalar = (str, int, float, bool, type(None))
        ctx = {k: v if isinstance(v, scalar) else str(v) for k, v in self.context.items()}
        return {"code": self.code, "message": self.message, "context": ctx}


# ------------------------------------------------------------------ validation (CP-03, CP-04)
class DomainValidationError(DomainError):
    """A value is malformed or violates a business rule."""

    default_code = "VALIDATION_ERROR"


class MoneyParseError(DomainValidationError):
    """A money string cannot be turned into whole rupiah (FS-CV-01)."""

    default_code = "MONEY_PARSE_ERROR"


class DateParseError(DomainValidationError):
    """A date string cannot be parsed as an Indonesian day/month/year date (FS-CV-03)."""

    default_code = "DATE_PARSE_ERROR"


class NpwpError(DomainValidationError):
    """An NPWP or NITKU has the wrong length or characters (FS-CV-04/05)."""

    default_code = "NPWP_INVALID"


class TerbilangError(DomainValidationError):
    """An amount-in-words string cannot be parsed (FS-CV-06)."""

    default_code = "TERBILANG_PARSE_ERROR"


class RulesError(DomainValidationError):
    """A rules file (``rules/*.yaml``) is missing, malformed or inconsistent."""

    default_code = "RULES_INVALID"


# ------------------------------------------------------------------ lifecycle and models
class InvalidTransition(DomainError):
    """The document state machine refused an event (FS-CM-02).

    Codes: ``INVALID_TRANSITION`` (pair not in the table) or ``RETRY_LIMIT_REACHED``.
    ``context`` always holds ``current`` and ``event``.
    """

    default_code = "INVALID_TRANSITION"


class InvalidModelOutput(DomainError):
    """A model returned output that does not match the expected schema (FS-AD-01)."""

    default_code = "INVALID_MODEL_OUTPUT"


class LicenseViolation(DomainError):
    """A dataset, font or model would be used against its licence (blueprint §4.1)."""

    default_code = "LICENSE_VIOLATION"


class CalibratorMismatch(DomainError):
    """A calibrator artefact was trained on different signals than it now receives."""

    default_code = "CALIBRATOR_MISMATCH"


# ------------------------------------------------------------------ external calls
class RetryableError(DomainError):
    """A temporary failure. The job queue retries ONLY subclasses of this class."""

    default_code = "RETRYABLE_ERROR"


class ExternalTimeout(RetryableError):
    """An external call (LLM, storage, OCR service) timed out."""

    default_code = "EXTERNAL_TIMEOUT"


class RateLimited(RetryableError):
    """The provider asked us to slow down. Put ``retry_after_s`` in context when known."""

    default_code = "RATE_LIMITED"


class ProviderUnavailable(RetryableError):
    """The provider is down or returned a 5xx status."""

    default_code = "PROVIDER_UNAVAILABLE"


class PermanentExternalError(DomainError):
    """An external call failed in a way retrying cannot fix (bad request, auth, policy)."""

    default_code = "PERMANENT_EXTERNAL_ERROR"
