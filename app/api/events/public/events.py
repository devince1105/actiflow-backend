# app/api/events/public/events.py
# 活動列表 / 搜尋（Public）

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.core.db import get_db
from app.core.constants.event_status import EventStatus
from app.models.event.event import Event
from app.models.submission.submission import Submission
from app.models.submission.enums import SubmissionStatus
from app.schemas.common.pagination import PaginatedResponse

from app.schemas.event.public.event_list_item import (
    EventPublicListItem,
    EventPublicLocation,
    EventPublicConfig,
    EventPublicTime,
)
from app.schemas.event.public.event_category import PublicEventCategory
from app.schemas.organizer.public.organizer_public import OrganizerPublic


router = APIRouter(
    prefix="/public/events",
    tags=["Public - Events"],
)


# -------------------------------------------------------------------
# Public: List published events
# -------------------------------------------------------------------
@router.get("", response_model=PaginatedResponse[EventPublicListItem])
def list_public_events(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    """
    公開活動列表（僅顯示已發布的活動）
    - 僅回傳列表頁需要的欄位
    - 包含報名人數統計 (registered_count)
    """

    # 1. Subquery: 每個活動的有效報名數
    # ------------------------------------------------
    submission_count_subq = (
        db.query(
            Submission.event_uuid.label("event_uuid"),
            func.count(Submission.id).label("registered_count"),
        )
        .filter(
            Submission.is_deleted == False,
            # 只算這幾種狀態視為「佔名額」
            Submission.status.in_([
                SubmissionStatus.pending,       # 佔用名額中
                SubmissionStatus.email_verified,
                SubmissionStatus.paid,
                SubmissionStatus.completed,
            ]),
        )
        .group_by(Submission.event_uuid)
        .subquery()
    )

    # 2. Main Query: Event + Join Subquery
    # ------------------------------------------------
    query = (
        db.query(
            Event,
            func.coalesce(submission_count_subq.c.registered_count, 0).label("registered_count"),
        )
        .outerjoin(
            submission_count_subq,
            submission_count_subq.c.event_uuid == Event.uuid,
        )
        .options(
            selectinload(Event.media),
            selectinload(Event.event_category),
            selectinload(Event.organizer),
        )
        .filter(
            Event.status == EventStatus.PUBLISHED,
            Event.is_deleted == False,
            Event.is_active == True,
        )
    )

    # 3. Count Total (Fix: separate count query)
    # ------------------------------------------------
    # query.count() 會因為 select 了多個欄位而出錯，這裡使用獨立查詢
    total = db.query(func.count(Event.id)).filter(
        Event.status == EventStatus.PUBLISHED,
        Event.is_deleted == False,
        Event.is_active == True,
    ).scalar()

    # 4. Execute Query
    # ------------------------------------------------
    results = (
        query
        .order_by(
            Event.start_date.asc(),
            Event.created_at.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items: list[EventPublicListItem] = []

    for row in results:
        event = row[0]  # Event model instance
        reg_count = row[1]  # registered_count (int)

        # ------------------------------
        # Cover image
        # ------------------------------
        cover_image_url = None
        for media in event.media:
            if media.is_cover and not media.is_deleted:
                cover_image_url = media.url
                break

        # ------------------------------
        # Location
        # ------------------------------
        location = (
            EventPublicLocation(name=event.location)
            if event.location
            else None
        )

        # ------------------------------
        # Time Display
        # ------------------------------
        time_display = None
        if event.start_date:
            time_display = event.start_date.strftime("%Y-%m-%d %H:%M")
            if event.end_date:
                time_display += f" ~ {event.end_date.strftime('%H:%M')}"

        time_info = EventPublicTime(
            start_date=event.start_date,
            end_date=event.end_date,
            display=time_display
        )

        # ------------------------------
        # Organizer
        # ------------------------------
        organizer_info = None
        if event.organizer:
            organizer_info = OrganizerPublic(
                uuid=event.organizer.uuid,
                name=event.organizer.name,
                slug=event.organizer.slug,
                logo_url=event.organizer.logo_url
            )

        # ------------------------------
        # Category config
        # ------------------------------
        config = None
        if event.event_category:
            config = EventPublicConfig(
                category=PublicEventCategory(
                    code=event.event_category.code,
                    slug=event.event_category.slug,
                    label=(
                        event.event_category.display_label_zh
                        or event.event_category.label_zh
                    ),
                    color=event.event_category.color,
                    icon=event.event_category.icon,
                )
            )
        
        # ------------------------------
        # Capacity
        # ------------------------------
        capacity = event.config.get("capacity") if event.config else None

        items.append(
            EventPublicListItem(
                uuid=event.uuid,
                event_code=event.event_code,
                name=event.name,
                description=event.description,
                cover_image_url=cover_image_url,
                time=time_info, 
                location=location,
                organizer=organizer_info,
                config=config,
                capacity=capacity,
                registered_count=reg_count,
            )
        )

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


# -------------------------------------------------------------------
# Public: Get event detail by event_code
# -------------------------------------------------------------------
@router.get("/{event_code}", response_model=EventPublicListItem)
def get_public_event(
    event_code: str,
    db: Session = Depends(get_db),
):
    # 1. Subquery
    submission_count_subq = (
        db.query(
            Submission.event_uuid.label("event_uuid"),
            func.count(Submission.id).label("registered_count"),
        )
        .filter(
            Submission.is_deleted == False,
            Submission.status.in_([
                SubmissionStatus.pending,
                SubmissionStatus.email_verified,
                SubmissionStatus.paid,
                SubmissionStatus.completed,
            ]),
        )
        .group_by(Submission.event_uuid)
        .subquery()
    )

    # 2. Main Query
    query = (
        db.query(
            Event,
            func.coalesce(submission_count_subq.c.registered_count, 0).label("registered_count"),
        )
        .outerjoin(
            submission_count_subq,
            submission_count_subq.c.event_uuid == Event.uuid,
        )
        .options(
            selectinload(Event.media),
            selectinload(Event.event_category),
            selectinload(Event.organizer),
        )
        .filter(
            Event.event_code == event_code,
            Event.status == EventStatus.PUBLISHED,
            Event.is_deleted == False,
            Event.is_active == True,
        )
    )
    
    row = query.first()

    if not row:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event = row[0]
    reg_count = row[1]

    # ------------------------------
    # Cover image
    # ------------------------------
    cover_image_url = None
    for media in event.media:
        if media.is_cover and not media.is_deleted:
            cover_image_url = media.url
            break

    # ------------------------------
    # Location
    # ------------------------------
    location = (
        EventPublicLocation(name=event.location)
        if event.location
        else None
    )

    # ------------------------------
    # Time Display
    # ------------------------------
    time_display = None
    if event.start_date:
        time_display = event.start_date.strftime("%Y-%m-%d %H:%M")
        if event.end_date:
            time_display += f" ~ {event.end_date.strftime('%H:%M')}"

    time_info = EventPublicTime(
        start_date=event.start_date,
        end_date=event.end_date,
        display=time_display
    )

    # ------------------------------
    # Organizer
    # ------------------------------
    organizer_info = None
    if event.organizer:
        organizer_info = OrganizerPublic(
            uuid=event.organizer.uuid,
            name=event.organizer.name,
            slug=event.organizer.slug,
            logo_url=event.organizer.logo_url
        )

    # ------------------------------
    # Category config
    # ------------------------------
    config = None
    if event.event_category:
        config = EventPublicConfig(
            category=PublicEventCategory(
                code=event.event_category.code,
                slug=event.event_category.slug,
                label=(
                    event.event_category.display_label_zh
                    or event.event_category.label_zh
                ),
                color=event.event_category.color,
                icon=event.event_category.icon,
            )
        )
    
    # Capacity
    capacity = event.config.get("capacity") if event.config else None

    return EventPublicListItem(
        uuid=event.uuid,
        event_code=event.event_code,
        name=event.name,
        description=event.description,
        cover_image_url=cover_image_url,
        time=time_info,
        location=location,
        organizer=organizer_info,
        config=config,
        capacity=capacity,
        registered_count=reg_count,
    )
