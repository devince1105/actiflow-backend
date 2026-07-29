from math import ceil
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.dependencies import require_super_admin
from app.models.event.event import Event
from app.models.organizer.organizer import Organizer
from app.models.submission.submission import Submission
from app.models.system.system_audit_log import SystemAuditLog
from app.schemas.admin.events import (
    AdminEventListItem,
    AdminEventListResponse,
    AdminEventModerationRequest,
)


router = APIRouter(
    prefix="/admin/events",
    tags=["Admin - Events"],
)


@router.get("", response_model=AdminEventListResponse)
def list_admin_events(
    search: str = Query(default="", max_length=200),
    event_status: str = Query(
        default="all",
        alias="status",
        pattern="^(all|draft|published|closed)$",
    ),
    timing: str = Query(
        default="all",
        pattern="^(all|upcoming|past)$",
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin=Depends(require_super_admin),
):
    now = func.now()
    query = (
        db.query(
            Event.uuid,
            Event.event_code,
            Event.name,
            Event.organizer_uuid,
            Organizer.name.label("organizer_name"),
            Event.status,
            Event.is_active,
            Event.start_date,
            Event.end_date,
            Event.registration_deadline,
            Event.max_capacity,
            Event.current_attendance,
        )
        .join(Organizer, Organizer.uuid == Event.organizer_uuid)
        .filter(
            Event.is_deleted == False,
            Organizer.is_deleted == False,
        )
    )

    normalized_search = search.strip()
    if normalized_search:
        pattern = f"%{normalized_search}%"
        query = query.filter(
            or_(
                Event.name.ilike(pattern),
                Event.event_code.ilike(pattern),
                Organizer.name.ilike(pattern),
            )
        )
    if event_status != "all":
        query = query.filter(Event.status == event_status)
    if timing == "upcoming":
        query = query.filter(
            or_(
                Event.end_date >= now,
                and_(Event.end_date.is_(None), Event.start_date >= now),
            )
        )
    elif timing == "past":
        query = query.filter(
            or_(
                Event.end_date < now,
                and_(Event.end_date.is_(None), Event.start_date < now),
            )
        )

    total = query.count()
    rows = (
        query.order_by(Event.start_date.desc(), Event.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    event_uuids = [row.uuid for row in rows]
    submission_counts: dict = {}
    if event_uuids:
        submission_counts = dict(
            db.query(Submission.event_uuid, func.count(Submission.id))
            .filter(
                Submission.event_uuid.in_(event_uuids),
                Submission.is_deleted == False,
            )
            .group_by(Submission.event_uuid)
            .all()
        )

    return AdminEventListResponse(
        items=[
            AdminEventListItem(
                uuid=row.uuid,
                event_code=row.event_code,
                name=row.name,
                organizer_uuid=row.organizer_uuid,
                organizer_name=row.organizer_name,
                status=row.status,
                is_active=row.is_active,
                start_date=row.start_date,
                end_date=row.end_date,
                registration_deadline=row.registration_deadline,
                max_capacity=row.max_capacity,
                current_attendance=row.current_attendance,
                submissions_count=submission_counts.get(row.uuid, 0),
            )
            for row in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
    )


@router.patch("/{event_uuid}/moderation", response_model=AdminEventListItem)
def moderate_admin_event(
    event_uuid: UUID,
    data: AdminEventModerationRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_super_admin),
):
    event = (
        db.query(Event)
        .filter(Event.uuid == event_uuid, Event.is_deleted == False)
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.status == data.status:
        raise HTTPException(
            status_code=409,
            detail=f"Event is already {data.status}",
        )

    previous_status = event.status
    event.status = data.status
    event.updated_by = UUID(admin["uuid"])
    event.updated_by_role = "super_admin"
    db.add(
        SystemAuditLog(
            audit_code=f"AUD-{uuid4().hex.upper()}",
            user_uuid=UUID(admin["uuid"]),
            user_email=admin["email"],
            user_role="super_admin",
            action=(
                "force_close_event"
                if data.status == "closed"
                else "restore_published_event"
            ),
            target_type="Event",
            target_uuid=event.uuid,
            before_data={"status": previous_status},
            after_data={"status": data.status},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            extra={"reason": data.reason},
        )
    )
    db.commit()
    db.refresh(event)

    submissions_count = (
        db.query(func.count(Submission.id))
        .filter(
            Submission.event_uuid == event.uuid,
            Submission.is_deleted == False,
        )
        .scalar()
        or 0
    )
    return AdminEventListItem(
        uuid=event.uuid,
        event_code=event.event_code,
        name=event.name,
        organizer_uuid=event.organizer_uuid,
        organizer_name=event.organizer.name,
        status=event.status,
        is_active=event.is_active,
        start_date=event.start_date,
        end_date=event.end_date,
        registration_deadline=event.registration_deadline,
        max_capacity=event.max_capacity,
        current_attendance=event.current_attendance,
        submissions_count=submissions_count,
    )
