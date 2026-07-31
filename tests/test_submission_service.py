from uuid import uuid4
from fastapi import BackgroundTasks
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.orm.attributes import set_committed_value

from app.core.exceptions import ActiFlowBusinessException, ActiFlowErrorCode
from app.crud.submission.crud_submission_status import assert_status_transition
from app.models.auth.email_verification import EmailVerification
from app.models.event.event import Event
from app.models.event.event_category import EventCategory
from app.models.organizer.organizer import Organizer
from app.models.submission.submission import Submission
from app.models.submission.submission_audit import SubmissionAuditLog
from app.services.submission.submission_service import SubmissionService


class _Result:
    def __init__(self, rowcount: int):
        self.rowcount = rowcount


class _FakeDb:
    def __init__(self, rowcount: int = 1):
        self.rowcount = rowcount
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)
        return _Result(self.rowcount)


def test_reopen_requires_an_available_capacity_slot():
    db = _FakeDb(rowcount=0)

    with pytest.raises(ActiFlowBusinessException) as exc:
        SubmissionService._adjust_capacity_for_transition(
            db, uuid4(), "canceled", "pending"
        )

    assert exc.value.code == "EVENT_FULL"


def test_cancel_releases_capacity():
    db = _FakeDb()

    SubmissionService._adjust_capacity_for_transition(
        db, uuid4(), "pending", "canceled"
    )

    assert len(db.statements) == 1


def test_rejected_submission_can_be_reopened():
    assert_status_transition(current="rejected", target="pending")


def test_naive_registration_deadline_does_not_raise_type_error():
    event = SimpleNamespace(
        status="published",
        current_attendance=0,
        max_capacity=10,
        registration_deadline=datetime.now() - timedelta(minutes=1),
    )

    assert SubmissionService.can_register(event) is False


def _create_registration_event(db, *, capacity: int = 10) -> Event:
    unique = uuid4().hex
    organizer = Organizer(
        name=f"Submission Service Organizer {unique[:8]}",
        status="active",
    )
    category = EventCategory(
        code=f"SUBMISSION_{unique[:12].upper()}",
        slug=f"submission-{unique[:12]}",
        label_zh="報名服務測試",
        label_en="Submission Service Test",
        color="slate",
        sort_order=999,
    )
    db.add_all([organizer, category])
    db.flush()

    event = Event(
        event_code=f"SUB-{unique[:10].upper()}",
        name="Submission lifecycle test",
        slug=f"submission-lifecycle-{unique}",
        status="published",
        organizer_uuid=organizer.uuid,
        event_category_uuid=category.uuid,
        start_date=datetime.now(timezone.utc) + timedelta(days=7),
        end_date=datetime.now(timezone.utc) + timedelta(days=8),
        registration_deadline=datetime.now(timezone.utc) + timedelta(days=6),
        max_capacity=capacity,
        current_attendance=0,
    )
    db.add(event)
    db.flush()
    return event


def _register(db, event: Event, email: str) -> Submission:
    return SubmissionService.register_event(
        db=db,
        event_uuid=event.uuid,
        user_email=email,
        values=[],
    )


def test_capacity_is_enforced_when_a_competing_registration_saw_a_stale_slot(db):
    event = _create_registration_event(db, capacity=1)
    first = _register(db, event, "capacity-first@example.com")
    assert first.status.value == "pending"

    db.refresh(event)
    assert event.current_attendance == 1

    # Simulate another request that read the event before the first request
    # committed. The service's conditional UPDATE must remain authoritative.
    set_committed_value(event, "current_attendance", 0)

    with pytest.raises(ActiFlowBusinessException) as exc:
        _register(db, event, "capacity-competing@example.com")

    assert exc.value.code == ActiFlowErrorCode.EVENT_FULL
    assert exc.value.status_code == 400


def test_duplicate_registration_returns_conflict(db):
    event = _create_registration_event(db, capacity=5)
    _register(db, event, "duplicate@example.com")

    with pytest.raises(ActiFlowBusinessException) as exc:
        _register(db, event, "duplicate@example.com")

    assert exc.value.code == ActiFlowErrorCode.ALREADY_REGISTERED
    assert exc.value.status_code == 409


def test_registration_creates_email_verification(db):
    event = _create_registration_event(db)
    submission = _register(db, event, "verify@example.com")

    verification = (
        db.query(EmailVerification)
        .filter(
            EmailVerification.ref_type == "submission",
            EmailVerification.ref_uuid == submission.uuid,
        )
        .one()
    )

    assert verification.email == "verify@example.com"
    assert verification.token
    assert verification.is_used is False
    assert verification.verified_at is None
    expires_at = verification.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    assert expires_at > datetime.now(timezone.utc)


def test_status_change_creates_audit_entry(db):
    event = _create_registration_event(db)
    submission = _register(db, event, "audit@example.com")
    actor_uuid = uuid4()

    updated = SubmissionService.update_status(
        db=db,
        submission_uuid=submission.uuid,
        target_status="canceled",
        actor_id=actor_uuid,
        actor_role="user",
        reason="Changed plans",
    )

    audit = (
        db.query(SubmissionAuditLog)
        .filter(SubmissionAuditLog.submission_uuid == submission.uuid)
        .one()
    )

    assert updated.status.value == "canceled"
    assert audit.actor_uuid == actor_uuid
    assert audit.actor_role == "user"
    assert audit.action_type == "canceled"
    assert audit.old_status == "pending"
    assert audit.new_status == "canceled"
    assert audit.reason == "Changed plans"


def test_bulk_approve_uses_completed_status_and_queues_notification(db):
    event = _create_registration_event(db)
    submission = _register(db, event, "bulk-approve@example.com")
    background_tasks = BackgroundTasks()
    SubmissionService.update_status(
        db=db,
        submission_uuid=submission.uuid,
        target_status="email_verified",
        actor_role="system",
        background_tasks=background_tasks,
    )
    SubmissionService.update_status(
        db=db,
        submission_uuid=submission.uuid,
        target_status="paid",
        actor_role="admin",
        background_tasks=background_tasks,
    )

    result = SubmissionService.bulk_action(
        db=db,
        event_uuid=event.uuid,
        submission_uuids=[submission.uuid],
        action="approve",
        actor_id=uuid4(),
        actor_role="organizer",
        background_tasks=background_tasks,
    )

    db.refresh(submission)
    assert result["success_count"] == 1
    assert submission.status.value == "completed"
    assert len(background_tasks.tasks) == 3
