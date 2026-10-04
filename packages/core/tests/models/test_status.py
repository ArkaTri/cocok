"""CP-02 · FS-CM-02 document state machine.

The oracle below is copied from FUNCTION_SPECS FS-CM-02 by hand, NOT imported from the code, so
a typo in the implementation cannot also hide in the test.
"""

from collections import deque
from itertools import product

import pytest
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule

from cocok_core.errors import InvalidTransition
from cocok_core.models.status import (
    MAX_RETRIES,
    TERMINAL,
    DocumentStatus,
    Event,
    allowed_events,
    transition,
)

pytestmark = pytest.mark.cp02

S, E = DocumentStatus, Event
ORACLE: dict[tuple[DocumentStatus, Event], DocumentStatus] = {
    (S.UPLOADED, E.ENQUEUE): S.QUEUED,
    (S.QUEUED, E.START): S.PROCESSING,
    (S.PROCESSING, E.EXTRACTED): S.EXTRACTED,
    (S.PROCESSING, E.FAIL): S.FAILED,
    (S.EXTRACTED, E.AUTO_APPROVE): S.AUTO_APPROVED,
    (S.EXTRACTED, E.NEED_REVIEW): S.NEEDS_REVIEW,
    (S.NEEDS_REVIEW, E.APPROVE): S.APPROVED,
    (S.NEEDS_REVIEW, E.REJECT): S.REJECTED,
    (S.AUTO_APPROVED, E.POST): S.POSTED,
    (S.APPROVED, E.POST): S.POSTED,
    (S.FAILED, E.RETRY): S.QUEUED,
}
ALL_PAIRS = list(product(DocumentStatus, Event))


def test_oracle_and_enums_have_expected_size() -> None:
    assert len(DocumentStatus) == 10
    assert len(Event) == 10
    assert len(ALL_PAIRS) == 100
    assert len(ORACLE) == 11


@pytest.mark.parametrize(("current", "event"), ALL_PAIRS, ids=str)
def test_every_pair_matches_the_oracle(current: DocumentStatus, event: Event) -> None:
    expected = ORACLE.get((current, event))
    if expected is None:
        with pytest.raises(InvalidTransition) as exc:
            transition(current, event)
        assert exc.value.code == "INVALID_TRANSITION"
        assert exc.value.context == {"current": str(current), "event": str(event)}
    else:
        assert transition(current, event) is expected


@pytest.mark.parametrize("retry_count", range(MAX_RETRIES))
def test_retry_allowed_below_limit(retry_count: int) -> None:
    assert transition(S.FAILED, E.RETRY, retry_count=retry_count) is S.QUEUED


@pytest.mark.parametrize("retry_count", [MAX_RETRIES, MAX_RETRIES + 1, 99])
def test_retry_refused_at_limit(retry_count: int) -> None:
    with pytest.raises(InvalidTransition) as exc:
        transition(S.FAILED, E.RETRY, retry_count=retry_count)
    assert exc.value.code == "RETRY_LIMIT_REACHED"
    assert exc.value.context["retry_count"] == retry_count


def test_retry_count_is_ignored_for_other_events() -> None:
    assert transition(S.UPLOADED, E.ENQUEUE, retry_count=99) is S.QUEUED


def test_negative_retry_count_is_a_caller_bug() -> None:
    with pytest.raises(ValueError, match="retry_count"):
        transition(S.FAILED, E.RETRY, retry_count=-1)


@pytest.mark.parametrize("status", list(DocumentStatus))
def test_allowed_events_agrees_with_oracle(status: DocumentStatus) -> None:
    assert allowed_events(status) == {e for (s, e) in ORACLE if s is status}


def test_terminal_statuses_accept_nothing() -> None:
    assert {S.REJECTED, S.POSTED} == TERMINAL
    for status in TERMINAL:
        assert allowed_events(status) == frozenset()


def test_every_status_is_reachable_from_uploaded() -> None:
    seen, queue = {S.UPLOADED}, deque([S.UPLOADED])
    while queue:
        current = queue.popleft()
        for event in allowed_events(current):
            nxt = transition(current, event)
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    assert seen == set(DocumentStatus)


def test_every_non_terminal_status_can_reach_a_terminal_one() -> None:
    for start in set(DocumentStatus) - TERMINAL:
        seen, queue = {start}, deque([start])
        while queue:
            current = queue.popleft()
            for event in allowed_events(current):
                nxt = transition(current, event)
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        assert seen & TERMINAL, f"{start} can never finish"


class DocumentLifecycle(RuleBasedStateMachine):
    """Hypothesis fires random event sequences at one document and checks the invariants."""

    def __init__(self) -> None:
        super().__init__()
        self.status = S.UPLOADED
        self.retries = 0

    @rule(event=st.sampled_from(Event))
    def fire(self, event: Event) -> None:
        before = self.status
        try:
            after = transition(before, event, retry_count=self.retries)
        except InvalidTransition:
            # Refused events must be exactly the ones the oracle refuses (or the retry limit).
            limit_hit = event is E.RETRY and before is S.FAILED and self.retries >= MAX_RETRIES
            assert (before, event) not in ORACLE or limit_hit
            return
        assert ORACLE[(before, event)] is after
        if event is E.RETRY:
            self.retries += 1
        self.status = after

    @invariant()
    def status_is_known(self) -> None:
        assert self.status in DocumentStatus

    @invariant()
    def retries_never_exceed_limit(self) -> None:
        assert self.retries <= MAX_RETRIES


TestDocumentLifecycle = DocumentLifecycle.TestCase
