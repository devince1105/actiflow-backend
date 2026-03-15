# app/crud/event/crud_event_content.py

from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.event.event import Event


# ---------------------------------------------------------
# Read
# ---------------------------------------------------------
def get_event_content(
    db: Session,
    *,
    event_uuid: UUID,
) -> dict:
    """
    取得活動內容（Event.content）
    """
    event = db.scalar(
        select(Event).where(Event.uuid == event_uuid)
    )

    if not event:
        return {"blocks": []}

    return event.content or {"blocks": []}


# ---------------------------------------------------------
# Replace (PUT)
# ---------------------------------------------------------
def replace_event_content(
    db: Session,
    *,
    event_uuid: UUID,
    content: dict,
) -> dict:
    """
    整包覆蓋活動內容（PUT）
    """
    event = db.scalar(
        select(Event).where(Event.uuid == event_uuid)
    )

    if not event:
        raise ValueError("Event not found")

    # 1️⃣ Organizer 編輯用（完整資料）
    event.content = content

    # 2️⃣ ✅ Public Snapshot（給 public event-detail 用）
    if event.config is None:
        event.config = {}

    event.config["content"] = content

    db.commit()
    db.refresh(event)

    return event.content


# ---------------------------------------------------------
# Patch (PATCH)
# ---------------------------------------------------------
def patch_event_content(
    db: Session,
    *,
    event_uuid: UUID,
    content: dict,
) -> dict:
    """
    PATCH：目前與 PUT 相同行為（保留未來彈性）
    """
    return replace_event_content(
        db,
        event_uuid=event_uuid,
        content=content,
    )


# ---------------------------------------------------------
# Delete (DELETE)
# ---------------------------------------------------------
def delete_event_content(
    db: Session,
    *,
    event_uuid: UUID,
) -> dict:
    """
    清空活動內容（保留結構）
    """
    event = db.scalar(
        select(Event).where(Event.uuid == event_uuid)
    )

    if not event:
        raise ValueError("Event not found")

    empty_content = {"blocks": []}

    # Organizer
    event.content = empty_content

    # ✅ Public Snapshot 也要清
    if event.config is None:
        event.config = {}

    event.config["content"] = empty_content

    db.commit()
    db.refresh(event)

    return event.content
