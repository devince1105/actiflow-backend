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
from app.models.event.event_field import EventField
from app.models.organizer.organizer import Organizer
from app.models.submission.submission import Submission
from app.models.submission.submission_audit import SubmissionAuditLog
from app.models.submission.submission_value import SubmissionValue
from app.services.submission.submission_service import SubmissionService
from app.api.utils.submission_code import generate_submission_code


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


def test_submission_codes_are_unique_within_the_same_second():
    first = generate_submission_code("EVT-TEST")
    second = generate_submission_code("EVT-TEST")

    assert first != second
    assert first.startswith("EVT-TEST-")
    assert second.startswith("EVT-TEST-")


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


def test_completed_submission_reopens_to_paid(db):
    event = _create_registration_event(db)
    submission = _register(db, event, "reopen-completed@example.com")
    submission.status = "completed"
    db.commit()

    reopened = SubmissionService.reopen_submission(
        db=db,
        submission_uuid=submission.uuid,
        actor_id=uuid4(),
        actor_role="organizer",
        reason="Review again",
    )

    assert reopened.status.value == "paid"
    assert reopened.notes == "Review again"


def test_rejected_submission_reopens_to_pending(db):
    event = _create_registration_event(db)
    submission = _register(db, event, "reopen-rejected@example.com")
    submission.status = "rejected"
    event.current_attendance = 0
    db.commit()

    reopened = SubmissionService.reopen_submission(
        db=db,
        submission_uuid=submission.uuid,
        actor_id=uuid4(),
        actor_role="organizer",
        reason="New information",
    )

    assert reopened.status.value == "pending"
    assert reopened.status_reason is None
    assert reopened.notes == "New information"


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


def _add_event_field(
    db,
    event: Event,
    *,
    field_key: str,
    field_type: str = "text",
    required: bool = False,
    options: list | None = None,
    validation: dict | None = None,
    is_active: bool = True,
    is_enabled: bool = True,
    sort_order: int = 0,
) -> EventField:
    field = EventField(
        event_uuid=event.uuid,
        field_key=field_key,
        label=field_key.replace("_", " ").title(),
        field_type=field_type,
        required=required,
        sort_order=sort_order,
        options=options or [],
        config={},
        validation=validation or {},
        is_active=is_active,
        is_enabled=is_enabled,
    )
    db.add(field)
    db.commit()
    return field


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


def test_inactive_event_cannot_accept_registration(db):
    event = _create_registration_event(db)
    event.is_active = False
    db.commit()

    with pytest.raises(ActiFlowBusinessException) as exc:
        _register(db, event, "inactive-event@example.com")

    assert exc.value.code == ActiFlowErrorCode.EVENT_NOT_FOUND
    assert exc.value.status_code == 404


def test_registration_requires_configured_required_fields(db):
    event = _create_registration_event(db)
    db.add(
        EventField(
            event_uuid=event.uuid,
            field_key="participant_name",
            label="Participant name",
            field_type="text",
            required=True,
            sort_order=1,
            options=[],
            config={},
            validation={},
            is_enabled=True,
        )
    )
    db.commit()

    with pytest.raises(ActiFlowBusinessException) as exc:
        _register(db, event, "missing-required@example.com")

    assert exc.value.code == ActiFlowErrorCode.INVALID_SUBMISSION_DATA
    assert exc.value.status_code == 422
    assert exc.value.detail == {"missing_fields": ["participant_name"]}


def test_registration_requires_required_boolean_checkbox_to_be_checked(db):
    event = _create_registration_event(db)
    field = _add_event_field(
        db,
        event,
        field_key="terms_accepted",
        field_type="checkbox",
        required=True,
    )

    with pytest.raises(ActiFlowBusinessException) as exc:
        SubmissionService.register_event(
            db=db,
            event_uuid=event.uuid,
            user_email="unchecked-required@example.com",
            values=[SimpleNamespace(field_key=field.field_key, value=False)],
        )

    assert exc.value.detail == {"missing_fields": [field.field_key]}


def test_registration_rejects_duplicate_field_keys(db):
    event = _create_registration_event(db)
    duplicate_values = [
        SimpleNamespace(field_key="name", value="First"),
        SimpleNamespace(field_key="name", value="Second"),
    ]

    with pytest.raises(ActiFlowBusinessException) as exc:
        SubmissionService.register_event(
            db=db,
            event_uuid=event.uuid,
            user_email="duplicate-fields@example.com",
            values=duplicate_values,
        )

    assert exc.value.code == ActiFlowErrorCode.INVALID_SUBMISSION_DATA
    assert exc.value.status_code == 422


def test_registration_rejects_unknown_or_disabled_fields(db):
    event = _create_registration_event(db)
    _add_event_field(
        db,
        event,
        field_key="disabled_field",
        is_enabled=False,
    )

    for field_key in ("unknown_field", "disabled_field"):
        with pytest.raises(ActiFlowBusinessException) as exc:
            SubmissionService.register_event(
                db=db,
                event_uuid=event.uuid,
                user_email=f"{field_key}@example.com",
                values=[SimpleNamespace(field_key=field_key, value="value")],
            )

        assert exc.value.code == ActiFlowErrorCode.INVALID_SUBMISSION_DATA
        assert exc.value.detail == {"unknown_fields": [field_key]}


@pytest.mark.parametrize(
    ("field_type", "options", "value", "reason"),
    [
        ("email", [], "not-an-email", "invalid_email"),
        ("date", [], "2026-99-99", "invalid_date"),
        ("number", [], "not-a-number", "must_be_number"),
        ("select", ["A", "B"], "C", "invalid_option"),
        ("radio", [{"label": "A", "value": "a"}], "A", "invalid_option"),
        ("checkbox", ["A", "B"], ["A", "C"], "invalid_option"),
    ],
)
def test_registration_validates_field_types_and_options(
    db,
    field_type,
    options,
    value,
    reason,
):
    event = _create_registration_event(db)
    field = _add_event_field(
        db,
        event,
        field_key="contract_field",
        field_type=field_type,
        options=options,
    )

    with pytest.raises(ActiFlowBusinessException) as exc:
        SubmissionService.register_event(
            db=db,
            event_uuid=event.uuid,
            user_email=f"invalid-{uuid4().hex}@example.com",
            values=[SimpleNamespace(field_key=field.field_key, value=value)],
        )

    assert exc.value.detail == {
        "field_key": field.field_key,
        "reason": reason,
    }


def test_registration_enforces_length_and_number_bounds(db):
    event = _create_registration_event(db)
    text_field = _add_event_field(
        db,
        event,
        field_key="short_text",
        validation={"min_length": 2, "max_length": 4},
    )
    number_field = _add_event_field(
        db,
        event,
        field_key="age",
        field_type="number",
        validation={"min": 18, "max": 120},
    )

    for field, value, reason in (
        (text_field, "x", "too_short"),
        (text_field, "12345", "too_long"),
        (number_field, 17, "outside_min"),
        (number_field, 121, "outside_max"),
    ):
        with pytest.raises(ActiFlowBusinessException) as exc:
            SubmissionService._validate_field_value(field, value)
        assert exc.value.detail["reason"] == reason


def test_valid_dynamic_field_value_is_persisted(db):
    event = _create_registration_event(db)
    field = _add_event_field(
        db,
        event,
        field_key="category",
        field_type="select",
        required=True,
        options=["Landscape", "Portrait"],
    )

    submission = SubmissionService.register_event(
        db=db,
        event_uuid=event.uuid,
        user_email="valid-contract@example.com",
        values=[SimpleNamespace(field_key="category", value="Landscape")],
    )
    stored_value = (
        db.query(SubmissionValue)
        .filter(SubmissionValue.submission_uuid == submission.uuid)
        .one()
    )

    assert stored_value.event_field_uuid == field.uuid
    assert stored_value.field_key == "category"
    assert stored_value.value == "Landscape"


def test_public_event_detail_exposes_only_enabled_fields_in_order(client, db):
    event = _create_registration_event(db)
    _add_event_field(
        db,
        event,
        field_key="second_field",
        sort_order=20,
        validation={"max_length": 20},
    )
    _add_event_field(
        db,
        event,
        field_key="first_field",
        field_type="select",
        options=["A", "B"],
        sort_order=10,
    )
    _add_event_field(
        db,
        event,
        field_key="hidden_field",
        is_active=False,
        sort_order=0,
    )

    response = client.get(f"/public/event-detail/{event.event_code}")

    assert response.status_code == 200
    fields = response.json()["fields"]
    assert [field["field_key"] for field in fields] == [
        "first_field",
        "second_field",
    ]
    assert fields[0]["options"] == ["A", "B"]
    assert fields[1]["validation"] == {"max_length": 20}


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
