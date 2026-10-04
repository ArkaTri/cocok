"""Document lifecycle state machine: the ONLY authority on status changes (FS-CM-02).

The machine is a plain lookup table ``(current status, event) -> next status`` (blueprint §6.2).
No library: eleven rows are easier to read, test exhaustively and review than any framework, and
``core`` must stay dependency-light.

Diagram::

    UPLOADED --ENQUEUE--> QUEUED --START--> PROCESSING --EXTRACTED--> EXTRACTED
    PROCESSING --FAIL--> FAILED --RETRY (only while retry_count < 3)--> QUEUED
    EXTRACTED --AUTO_APPROVE--> AUTO_APPROVED --POST--> POSTED
    EXTRACTED --NEED_REVIEW--> NEEDS_REVIEW --APPROVE--> APPROVED --POST--> POSTED
                               NEEDS_REVIEW --REJECT--> REJECTED

Changing this table changes the product: it needs an ADR and a blueprint update in the same PR.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from cocok_core.errors import InvalidTransition


class DocumentStatus(StrEnum):
    """Where a document is in its lifecycle. Values are stored in the database as-is."""

    UPLOADED = "UPLOADED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    EXTRACTED = "EXTRACTED"
    AUTO_APPROVED = "AUTO_APPROVED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    POSTED = "POSTED"
    FAILED = "FAILED"


class Event(StrEnum):
    """Something that happened to a document and may move it to another status."""

    ENQUEUE = "ENQUEUE"
    START = "START"
    EXTRACTED = "EXTRACTED"
    FAIL = "FAIL"
    AUTO_APPROVE = "AUTO_APPROVE"
    NEED_REVIEW = "NEED_REVIEW"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    POST = "POST"
    RETRY = "RETRY"


MAX_RETRIES: Final = 3
"""A FAILED document may go back to QUEUED at most this many times."""

TERMINAL: Final[frozenset[DocumentStatus]] = frozenset(
    {DocumentStatus.REJECTED, DocumentStatus.POSTED}
)
"""Statuses that no event can leave."""

_S = DocumentStatus
_TRANSITIONS: Final[Mapping[tuple[DocumentStatus, Event], DocumentStatus]] = MappingProxyType(
    {
        (_S.UPLOADED, Event.ENQUEUE): _S.QUEUED,
        (_S.QUEUED, Event.START): _S.PROCESSING,
        (_S.PROCESSING, Event.EXTRACTED): _S.EXTRACTED,
        (_S.PROCESSING, Event.FAIL): _S.FAILED,
        (_S.EXTRACTED, Event.AUTO_APPROVE): _S.AUTO_APPROVED,
        (_S.EXTRACTED, Event.NEED_REVIEW): _S.NEEDS_REVIEW,
        (_S.NEEDS_REVIEW, Event.APPROVE): _S.APPROVED,
        (_S.NEEDS_REVIEW, Event.REJECT): _S.REJECTED,
        (_S.AUTO_APPROVED, Event.POST): _S.POSTED,
        (_S.APPROVED, Event.POST): _S.POSTED,
        (_S.FAILED, Event.RETRY): _S.QUEUED,
    }
)


def transition(current: DocumentStatus, event: Event, *, retry_count: int = 0) -> DocumentStatus:
    """Return the status a document moves to when ``event`` happens. Pure: no I/O, no mutation.

    Args:
        current: The document's status now.
        event: What happened.
        retry_count: How many times this document was already retried. Read only for RETRY.

    Returns:
        The next status.

    Raises:
        InvalidTransition: Code ``INVALID_TRANSITION`` if the pair is not in the table, or
            ``RETRY_LIMIT_REACHED`` if the event is RETRY and ``retry_count >= MAX_RETRIES``.
        ValueError: If ``retry_count`` is negative (a caller bug, not a domain situation).

    Example:
        >>> transition(DocumentStatus.UPLOADED, Event.ENQUEUE)
        <DocumentStatus.QUEUED: 'QUEUED'>
        >>> transition(DocumentStatus.POSTED, Event.APPROVE)
        Traceback (most recent call last):
        ...
        cocok_core.errors.InvalidTransition: [INVALID_TRANSITION] POSTED cannot handle APPROVE
        >>> transition(DocumentStatus.FAILED, Event.RETRY, retry_count=3)
        Traceback (most recent call last):
        ...
        cocok_core.errors.InvalidTransition: [RETRY_LIMIT_REACHED] retried 3 times already (max 3)
    """
    if retry_count < 0:
        msg = f"retry_count must be >= 0, got {retry_count}"
        raise ValueError(msg)
    target = _TRANSITIONS.get((current, event))
    if target is None:
        raise InvalidTransition(
            f"{current} cannot handle {event}", current=str(current), event=str(event)
        )
    if event is Event.RETRY and retry_count >= MAX_RETRIES:
        raise InvalidTransition(
            f"retried {retry_count} times already (max {MAX_RETRIES})",
            code="RETRY_LIMIT_REACHED",
            current=str(current),
            event=str(event),
            retry_count=retry_count,
        )
    return target


def allowed_events(status: DocumentStatus) -> frozenset[Event]:
    """Return the events ``status`` accepts (the UI uses this to decide which buttons to show).

    Args:
        status: Any document status.

    Returns:
        The events with a row in the table for ``status``; empty for terminal statuses.

    Example:
        >>> sorted(allowed_events(DocumentStatus.NEEDS_REVIEW))
        [<Event.APPROVE: 'APPROVE'>, <Event.REJECT: 'REJECT'>]
    """
    return frozenset(event for (source, event) in _TRANSITIONS if source is status)
