import pytest
from fastapi import HTTPException

from app.core.constants.event_status import EventStatus
from app.core.domain.event_status_guard import assert_event_status_transition


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (EventStatus.DRAFT, EventStatus.PENDING_REVIEW),
        (EventStatus.CHANGES_REQUESTED, EventStatus.PENDING_REVIEW),
        (EventStatus.PENDING_REVIEW, EventStatus.PUBLISHED),
        (EventStatus.PENDING_REVIEW, EventStatus.CHANGES_REQUESTED),
        (EventStatus.PUBLISHED, EventStatus.DRAFT),
        (EventStatus.PUBLISHED, EventStatus.CLOSED),
    ],
)
def test_event_review_transition_is_allowed(current, target):
    assert_event_status_transition(current=current, target=target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (EventStatus.DRAFT, EventStatus.PUBLISHED),
        (EventStatus.CHANGES_REQUESTED, EventStatus.PUBLISHED),
        (EventStatus.PENDING_REVIEW, EventStatus.CLOSED),
    ],
)
def test_event_review_cannot_be_bypassed(current, target):
    with pytest.raises(HTTPException):
        assert_event_status_transition(current=current, target=target)
