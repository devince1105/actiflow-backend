# app/api/organizers/organizer/submissions.py
# Organizer 後台 - 活動報名紀錄（Submissions）

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.core.db import get_db
from app.core.dependencies import require_current_organizer_admin

from app.models.event.event import Event
from app.models.submission.submission import Submission
from app.models.submission.submission_value import SubmissionValue

from app.schemas.submission.submission_response import SubmissionResponse
from app.schemas.submission.submission_mapper import to_submission_response
from app.schemas.common.pagination import PaginatedResponse

router = APIRouter(
    prefix="/events/{event_uuid}/submissions",
    tags=["Organizer - Submissions"],
)


@router.get("", response_model=PaginatedResponse[SubmissionResponse])
def list_event_submissions(
    event_uuid: UUID,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    membership=Depends(require_current_organizer_admin),
):
    """
    Organizer 後台 - 取得某活動的報名紀錄
    """

    # -------------------------------------------------
    # 1. 確認 Event 屬於該 Organizer
    # -------------------------------------------------
    event = (
        db.query(Event)
        .filter(
            Event.uuid == event_uuid,
            Event.organizer_uuid == membership.organizer_uuid,
            Event.is_deleted == False,
        )
        .first()
    )

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # -------------------------------------------------
    # 2. Query Submissions
    # -------------------------------------------------
    query = (
        db.query(Submission)
        .options(
            selectinload(Submission.values)
                .selectinload(SubmissionValue.field), # EventField
            selectinload(Submission.values)
                .selectinload(SubmissionValue.files), # SubmissionFile
        )
        .filter(
            Submission.event_uuid == event_uuid,
            Submission.is_deleted == False,
        )
    )

    total = query.count()

    submissions = (
        query
        .order_by(Submission.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # -------------------------------------------------
    # 3. Mapper → Response
    # -------------------------------------------------
    return PaginatedResponse(
        items=[to_submission_response(s) for s in submissions],
        total=total,
        page=page,
        page_size=page_size,
    )

    return submissions
