from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.core.dependencies import require_current_organizer_admin
from app.main import app
from app.models.event.event import Event
from app.models.event.event_category import EventCategory
from app.models.organizer.organizer import Organizer
from app.models.submission.submission import Submission
from app.services.submission.submission_service import SubmissionService


def _create_event(db, organizer: Organizer, *, capacity: int = 10) -> Event:
    unique = uuid4().hex
    category = EventCategory(
        code=f"CONTRACT_{unique[:12].upper()}",
        slug=f"contract-{unique[:12]}",
        label_zh="契約測試",
        label_en="Contract Test",
        color="slate",
        sort_order=999,
    )
    db.add(category)
    db.flush()

    event = Event(
        event_code=f"CONTRACT-{unique[:10].upper()}",
        name="Organizer submission contract",
        slug=f"organizer-submission-contract-{unique}",
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


def _create_submission(db, event: Event, *, status: str, email: str) -> Submission:
    submission = Submission(
        submission_code=f"CONTRACT-{uuid4().hex}",
        event_uuid=event.uuid,
        user_email=email,
        status=status,
        extra_data={},
    )
    db.add(submission)
    event.current_attendance += 1
    db.commit()
    db.refresh(submission)
    return submission


def test_organizer_can_get_approve_and_reopen_owned_submission(
    client,
    db,
    monkeypatch,
):
    organizer = Organizer(name=f"Contract Organizer {uuid4().hex[:8]}", status="active")
    db.add(organizer)
    db.flush()
    event = _create_event(db, organizer)
    submission = _create_submission(
        db,
        event,
        status="paid",
        email=f"contract+{uuid4().hex}@example.com",
    )
    membership = SimpleNamespace(organizer_uuid=organizer.uuid, user_uuid=uuid4())
    app.dependency_overrides[require_current_organizer_admin] = lambda: membership
    monkeypatch.setattr(SubmissionService, "_queue_notification", lambda *args, **kwargs: None)

    base = f"/organizers/{organizer.uuid}/events/{event.uuid}/submissions/{submission.uuid}"
    try:
        detail = client.get(base)
        assert detail.status_code == 200
        assert detail.json()["uuid"] == str(submission.uuid)
        assert detail.json()["status"] == "paid"

        approved = client.post(f"{base}/approve")
        assert approved.status_code == 200
        assert approved.json()["status"] == "completed"

        reopened = client.post(f"{base}/reopen", json={"reason": "Review again"})
        assert reopened.status_code == 200
        assert reopened.json()["status"] == "paid"
        assert reopened.json()["notes"] == "Review again"
    finally:
        app.dependency_overrides.pop(require_current_organizer_admin, None)


def test_organizer_can_reject_and_reopen_owned_submission(
    client,
    db,
    monkeypatch,
):
    organizer = Organizer(name=f"Reject Organizer {uuid4().hex[:8]}", status="active")
    db.add(organizer)
    db.flush()
    event = _create_event(db, organizer)
    submission = _create_submission(
        db,
        event,
        status="paid",
        email=f"reject+{uuid4().hex}@example.com",
    )
    membership = SimpleNamespace(organizer_uuid=organizer.uuid, user_uuid=uuid4())
    app.dependency_overrides[require_current_organizer_admin] = lambda: membership
    monkeypatch.setattr(SubmissionService, "_queue_notification", lambda *args, **kwargs: None)

    base = f"/organizers/{organizer.uuid}/events/{event.uuid}/submissions/{submission.uuid}"
    try:
        rejected = client.post(f"{base}/reject", json={"reason": "Missing details"})
        assert rejected.status_code == 200
        assert rejected.json()["status"] == "rejected"
        assert rejected.json()["status_reason"] == "Missing details"

        reopened = client.post(f"{base}/reopen", json={"reason": "Details received"})
        assert reopened.status_code == 200
        assert reopened.json()["status"] == "pending"
        assert reopened.json()["status_reason"] is None
        assert reopened.json()["notes"] == "Details received"
    finally:
        app.dependency_overrides.pop(require_current_organizer_admin, None)


def test_organizer_cannot_read_submission_from_another_organizer(client, db):
    allowed = Organizer(name=f"Allowed Organizer {uuid4().hex[:8]}", status="active")
    other = Organizer(name=f"Other Organizer {uuid4().hex[:8]}", status="active")
    db.add_all([allowed, other])
    db.flush()
    other_event = _create_event(db, other)
    submission = _create_submission(
        db,
        other_event,
        status="paid",
        email=f"boundary+{uuid4().hex}@example.com",
    )
    membership = SimpleNamespace(organizer_uuid=allowed.uuid, user_uuid=uuid4())
    app.dependency_overrides[require_current_organizer_admin] = lambda: membership

    try:
        response = client.get(
            f"/organizers/{allowed.uuid}/events/{other_event.uuid}/submissions/{submission.uuid}"
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(require_current_organizer_admin, None)
