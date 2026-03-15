# app/api/events/public/event_detail.py
# 給外部 / public

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.core.db import get_db
from app.core.constants.event_status import EventStatus
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

    # =====================================================
    # Category
    # =====================================================
    category = (
        EventCategoryPublic.model_validate(event.event_category)
        if event.event_category
        else None
    )

    # =====================================================
    # Time
    # =====================================================
    if event.end_date:
        display_time = (
            f"{event.start_date:%Y/%m/%d %H:%M} ～ "
            f"{event.end_date:%Y/%m/%d %H:%M}"
        )
    else:
        display_time = f"{event.start_date:%Y/%m/%d %H:%M}"

    time = EventTimePublic(
        start=event.start_date,
        end=event.end_date,
        display=display_time,
    )

    # =====================================================
    # Location
    # =====================================================
    location = (
        EventLocationPublic(
            name=event.location,
            address=event.location,
            city=None,
        )
        if event.location
        else None
    )

    # =====================================================
    # Organizer
    # =====================================================
    organizer = (
        OrganizerPublic.from_orm(event.organizer)
        if event.organizer
        else None
    )

    # =====================================================
    # Cover Image
    # =====================================================
    cover_media = next(
        (m for m in event.media if m.is_cover and not m.is_deleted),
        None,
    )
    cover_image_url = cover_media.url if cover_media else None

    # =====================================================
    # Event Content (Editor Blocks)
    # =====================================================
    content_blocks: list[EventContentBlockPublic] = []

    if isinstance(event.content, dict):
        raw_blocks = event.content.get("blocks", [])

        if isinstance(raw_blocks, list):
            for b in raw_blocks:
                content_blocks.append(
                EventContentBlockPublic(
                    id=b.get("id"),
                    type=b.get("type"),
                    title=b.get("title"),
                    data=b.get("data"),
                )
            )

    content = (
        EventContentPublic(blocks=content_blocks)
        if content_blocks
        else None
    )

    # =====================================================
    # Response
    # =====================================================
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
        registration_deadline=event.registration_deadline,
        content=content,
        extra=event.config or {},
    )
