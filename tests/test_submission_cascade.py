# tests/test_submission_cascade.py

import pytest
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.organizer.organizer import Organizer
from app.models.event.event import Event
from app.models.event.event_field import EventField
from app.models.submission.submission import Submission
from app.models.submission.submission_value import SubmissionValue
from app.models.submission.submission_file import SubmissionFile
from app.models.event.event_ticket import EventTicket
from app.models.file.file import File
from datetime import datetime, timedelta, timezone

now = datetime.now(timezone.utc)

@pytest.fixture
def db() -> Session:
    """
    使用真實 PostgreSQL（Neon test branch）
    每個 test 完成後 rollback，避免污染 DB
    """
    session = SessionLocal()
    try:
        yield session
        session.rollback()
    finally:
        session.close()


def test_submission_cascade_delete(db: Session):
    """
    驗證：
    - delete Submission
    - SubmissionValue / SubmissionFile / EventTicket 被 cascade 刪除
    - File 不會被刪（shared entity）
    """
    # ---------------------------------------------------------
    # 1️⃣ 建立 Organizer（補這段）
    # ---------------------------------------------------------
    organizer = Organizer(
        uuid=uuid4(),
        name="Test Organizer",
        status="approved",
    )
    db.add(organizer)
    db.flush()

    # ---------------------------------------------------------
    # 1️⃣ 建立 Event
    # ---------------------------------------------------------
    event = Event(
        uuid=uuid4(),
        event_code=f"EVT-{uuid4().hex[:8]}",
        name="Cascade Test Event",
        slug=f"cascade-test-event-{uuid4().hex[:6]}",
        status="published",
        organizer_uuid=organizer.uuid,  # ⭐ 關鍵
        
        # ⭐ 必填欄位補齊
        start_date=now,
        end_date=now + timedelta(days=1),
        registration_deadline=now + timedelta(hours=12),
        version=1,
    )
    db.add(event)
    db.flush()

    # ---------------------------------------------------------
    # 2️⃣ 建立 Submission
    # ---------------------------------------------------------
    submission = Submission(
        uuid=uuid4(),
        submission_code="TEST-SUB-001",
        event_uuid=event.uuid,
        user_email="test@example.com",
        status="pending",
        extra_data={},
        version=1,
    )
    db.add(submission)
    db.flush()

    # ---------------------------------------------------------
    # 3️⃣ 建立 SubmissionValue
    # ---------------------------------------------------------
    field = EventField(
        uuid=uuid4(),
        event_uuid=event.uuid,
        field_key="test_field",
        label="Test Field",
        field_type="text",
        version=1,
    )
    db.add(field)
    db.flush()

    value = SubmissionValue(
        uuid=uuid4(),
        submission_uuid=submission.uuid,
        event_field_uuid=field.uuid,
        field_key=field.field_key,  # ✅ 補這
        value="test value",
        version=1,
    )
    db.add(value)
    db.flush()

    # ---------------------------------------------------------
    # 4️⃣ 建立 File（shared entity）
    # ---------------------------------------------------------
    file = File(
        uuid=uuid4(),
        url="https://example.com/test.png",
        name="test.png",
    )
    db.add(file)
    db.flush()

    # ---------------------------------------------------------
    # 5️⃣ 建立 SubmissionFile（中介表）
    # ---------------------------------------------------------
    sub_file = SubmissionFile(
        uuid=uuid4(),
        submission_uuid=submission.uuid,
        submission_value_uuid=value.uuid,
        file_uuid=file.uuid,
    )
    db.add(sub_file)
    db.flush()

    # ---------------------------------------------------------
    # 6️⃣ 建立 EventTicket
    # ---------------------------------------------------------
    ticket = EventTicket(
        uuid=uuid4(),
        event_uuid=event.uuid,
        submission_uuid=submission.uuid,
        ticket_code="TICKET-001",
        holder_name="Test User",
    )
    db.add(ticket)
    db.commit()

    # ---------------------------------------------------------
    # 🔥 Act：刪除 Submission
    # ---------------------------------------------------------
    db.delete(submission)
    db.commit()

    # ---------------------------------------------------------
    # ✅ Assert：全部 cascade 行為
    # ---------------------------------------------------------

    # Submission
    stmt = select(Submission).where(Submission.uuid == submission.uuid)
    assert db.scalar(stmt) is None

    # SubmissionValue
    assert db.scalar(
        select(SubmissionValue).where(SubmissionValue.uuid == value.uuid)
    ) is None

    # SubmissionFile
    assert db.scalar(
        select(SubmissionFile).where(SubmissionFile.uuid == sub_file.uuid)
    ) is None

    # EventTicket
    assert db.scalar(
        select(EventTicket).where(EventTicket.uuid == ticket.uuid)
    ) is None

    # ❗ File 不應被刪（shared）
    assert db.scalar(select(File).where(File.uuid == file.uuid)) is not None
