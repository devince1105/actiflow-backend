from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.event.event_category import EventCategory
from app.models.event.event_media import EventMedia
from app.models.membership.organizer_membership import OrganizerMembership
from app.models.organizer.organizer import Organizer
from app.models.user.user import User


def test_owner_creates_draft_event_and_attaches_verified_cover(
    client,
    db: Session,
    monkeypatch,
):
    unique = uuid4().hex
    password = "owner-password-123"
    owner = User(
        email=f"event-owner+{unique}@example.com",
        password_hash=hash_password(password),
        is_active=True,
        is_email_verified=True,
        auth_provider="local",
        config={},
    )
    organizer = Organizer(
        name=f"活動主辦單位 {unique[:8]}",
        status="approved",
        is_active=True,
    )
    category = EventCategory(
        code=f"EVENT_{unique[:12].upper()}",
        slug=f"event-{unique[:12]}",
        label_zh="活動建立測試",
        label_en="Event creation test",
        color="slate",
        sort_order=999,
    )
    db.add_all([owner, organizer, category])
    db.flush()
    db.add(
        OrganizerMembership(
            user_uuid=owner.uuid,
            organizer_uuid=organizer.uuid,
            role="owner",
            is_active=True,
            is_suspended=False,
        )
    )
    db.commit()

    login = client.post(
        "/auth/login",
        json={"email": owner.email, "password": password},
    )
    assert login.status_code == 200

    start = datetime.now(timezone.utc) + timedelta(days=30)
    created = client.post(
        f"/organizers/{organizer.uuid}/events",
        json={
            "name": "秋季城市健行",
            "description": "以步行認識城市歷史與公共空間。",
            "event_category_uuid": str(category.uuid),
            "location": "台北車站東三門",
            "max_capacity": 120,
            "start_date": start.isoformat(),
            "end_date": (start + timedelta(hours=4)).isoformat(),
            "registration_deadline": (
                start - timedelta(days=2)
            ).isoformat(),
            "config": {},
        },
    )
    assert created.status_code == 200
    event = created.json()
    assert event["status"] == "draft"
    assert event["event_category_uuid"] == str(category.uuid)
    assert event["location"] == "台北車站東三門"
    assert event["max_capacity"] == 120

    cover_url = "https://media.example.com/uploads/event-cover/cover.webp"
    monkeypatch.setattr(
        "app.api.organizers.organizer.events.complete_image_upload",
        lambda **_kwargs: cover_url,
    )
    covered = client.put(
        f"/organizers/{organizer.uuid}/events/{event['uuid']}/cover",
        json={
            "object_key": (
                f"uploads/event-cover/{owner.uuid}/2026/07/cover.webp"
            )
        },
    )
    assert covered.status_code == 200
    assert covered.json()["cover_image_url"] == cover_url

    media = (
        db.query(EventMedia)
        .filter(EventMedia.event_uuid == event["uuid"])
        .one()
    )
    assert media.is_cover is True
    assert media.created_by == owner.uuid

    submitted = client.patch(
        f"/organizers/{organizer.uuid}/events/{event['uuid']}/submit-review"
    )
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "pending_review"
    assert submitted.json()["submitted_for_review_at"] is not None

    from app.core.dependencies import require_super_admin
    from app.main import app

    reviewer = User(
        email=f"event-reviewer+{unique}@example.com",
        password_hash=hash_password("reviewer-password-123"),
        is_active=True,
        is_email_verified=True,
        auth_provider="local",
        config={},
    )
    db.add(reviewer)
    db.commit()
    app.dependency_overrides[require_super_admin] = lambda: {
        "uuid": str(reviewer.uuid),
        "email": reviewer.email,
        "memberships": [{"type": "system", "role": "super_admin"}],
    }
    try:
        approved = client.post(
            f"/admin/events/{event['uuid']}/review",
            json={"decision": "approve", "reason": "活動資料完整"},
        )
    finally:
        app.dependency_overrides.pop(require_super_admin, None)

    assert approved.status_code == 200
    assert approved.json()["status"] == "published"
    assert approved.json()["review_reason"] == "活動資料完整"
