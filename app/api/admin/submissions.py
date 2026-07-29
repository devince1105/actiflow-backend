from math import ceil

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.dependencies import require_super_admin
from app.models.event.event import Event
from app.models.organizer.organizer import Organizer
from app.models.submission.enums import SubmissionStatus
from app.models.submission.submission import Submission
from app.schemas.admin.submissions import (
    AdminSubmissionListItem,
    AdminSubmissionListResponse,
)


router = APIRouter(
    prefix="/admin/submissions",
    tags=["Admin - Submissions"],
)


@router.get("", response_model=AdminSubmissionListResponse)
def list_admin_submissions(
    search: str = Query(default="", max_length=254),
    submission_status: str = Query(
        default="all",
        alias="status",
        pattern=(
            "^(all|pending|email_verified|paid|canceled|completed|"
            "waitlist|expired|rejected)$"
        ),
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin=Depends(require_super_admin),
):
    filters = [
        Submission.is_deleted == False,
        Event.is_deleted == False,
        Organizer.is_deleted == False,
    ]
    normalized_search = search.strip()
    if normalized_search:
        pattern = f"%{normalized_search}%"
        filters.append(
            or_(
                Submission.submission_code.ilike(pattern),
                Submission.user_email.ilike(pattern),
                Submission.submitted_by_email.ilike(pattern),
                Event.name.ilike(pattern),
                Event.event_code.ilike(pattern),
                Organizer.name.ilike(pattern),
            )
        )

    base_query = (
        db.query(Submission)
        .join(Event, Event.uuid == Submission.event_uuid)
        .join(Organizer, Organizer.uuid == Event.organizer_uuid)
        .filter(*filters)
    )
    status_rows = (
        db.query(Submission.status, func.count(Submission.id))
        .join(Event, Event.uuid == Submission.event_uuid)
        .join(Organizer, Organizer.uuid == Event.organizer_uuid)
        .filter(*filters)
        .group_by(Submission.status)
        .all()
    )
    status_counts = {
        row_status.value
        if isinstance(row_status, SubmissionStatus)
        else str(row_status): count
        for row_status, count in status_rows
    }

    if submission_status != "all":
        base_query = base_query.filter(Submission.status == submission_status)

    total = base_query.count()
    rows = (
        base_query.with_entities(
            Submission.uuid,
            Submission.submission_code,
            Submission.user_email,
            Submission.submitted_by_email,
            Submission.status,
            Submission.status_reason,
            Submission.event_uuid,
            Event.event_code,
            Event.name.label("event_name"),
            Event.organizer_uuid,
            Organizer.name.label("organizer_name"),
            Submission.submitted_at,
        )
        .order_by(Submission.submitted_at.desc(), Submission.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return AdminSubmissionListResponse(
        items=[
            AdminSubmissionListItem(
                uuid=row.uuid,
                submission_code=row.submission_code,
                user_email=row.user_email,
                submitted_by_email=row.submitted_by_email,
                status=(
                    row.status.value
                    if isinstance(row.status, SubmissionStatus)
                    else str(row.status)
                ),
                status_reason=row.status_reason,
                event_uuid=row.event_uuid,
                event_code=row.event_code,
                event_name=row.event_name,
                organizer_uuid=row.organizer_uuid,
                organizer_name=row.organizer_name,
                submitted_at=row.submitted_at,
            )
            for row in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
        status_counts=status_counts,
    )
