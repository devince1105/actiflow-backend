# app/api/events/public/event_detail.py
# 給外部 / public

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from uuid import UUID

from app.core.db import get_db
from app.core.constants.event_status import EventStatus
from app.core.datetime_utils import as_taipei, as_utc
from app.models.event.event import Event

from app.schemas.event.public.event_detail import (
    EventDetailPublic,
    EventTimePublic,
    EventLocationPublic,
    EventContentPublic,
    EventContentBlockPublic,
)
from app.schemas.organizer.public.organizer_public import OrganizerPublic
from app.schemas.event.category.event_category_public import EventCategoryPublic

router = APIRouter(
    prefix="/public/event-detail",
    tags=["Public Events"],
)

@router.get("/{event_code}", response_model=EventDetailPublic)
def get_public_event_detail_by_code(
    event_code: str,
    db: Session = Depends(get_db),
):
    """
    公開活動內頁（Public）
    - 使用 event_code
    - 僅限 published event
    - 純靜態資料提供，不包含 User Context 以支援快取或 CDN 加速
    """

    event = (
        db.query(Event)
        .options(
            selectinload(Event.media),
            selectinload(Event.organizer),
            selectinload(Event.event_category),
        )
        .filter(
            Event.event_code == event_code,
            Event.status == EventStatus.PUBLISHED,
            Event.is_deleted == False,
        )
        .first()
    )

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # 1. Category
    category = (
        EventCategoryPublic.model_validate(event.event_category)
        if event.event_category
        else None
    )

    # 2. Time
    local_start = as_taipei(event.start_date)
    local_end = as_taipei(event.end_date) if event.end_date else None
    if local_end:
        display_time = (
            f"{local_start:%Y/%m/%d %H:%M} ～ "
            f"{local_end:%Y/%m/%d %H:%M}"
        )
    else:
        display_time = f"{local_start:%Y/%m/%d %H:%M}"

    time = EventTimePublic(
        start=as_utc(event.start_date),
        end=as_utc(event.end_date),
        display=display_time,
    )

    # 3. Location
    location = (
        EventLocationPublic(
            name=event.location,
            address=event.location,
            city=None,
        )
        if event.location
        else None
    )

    # 4. Organizer
    organizer = (
        OrganizerPublic.model_validate(event.organizer)
        if event.organizer
        else None
    )

    # 5. Cover Image
    cover_media = next(
        (m for m in event.media if m.is_cover and not m.is_deleted),
        None,
    )
    cover_image_url = cover_media.url if cover_media else None

    # 6. Event Content
    content_blocks: list[EventContentBlockPublic] = []
    if isinstance(event.content, dict):
        raw_blocks = event.content.get("blocks", [])
        if isinstance(raw_blocks, list):
            for b in raw_blocks:
                if not isinstance(b, dict) or not isinstance(b.get("type"), str):
                    continue
                content_blocks.append(
                    EventContentBlockPublic(
                        id=b.get("id"),
                        type=b.get("type"),
                        title=b.get("title"),
                        data=b.get("data"),
                    )
                )
    content = EventContentPublic(blocks=content_blocks) if content_blocks else None

    # 7. Response
    return EventDetailPublic(
        uuid=str(event.uuid),
        event_code=event.event_code,
        name=event.name,
        description=event.description,
        cover_image_url=cover_image_url,
        category=category,
        time=time,
        location=location,
        organizer=organizer,
        registration_deadline=as_utc(event.registration_deadline),
        content=content,
        max_capacity=event.max_capacity,
        current_attendance=event.current_attendance,
        extra=event.config or {},
    )
