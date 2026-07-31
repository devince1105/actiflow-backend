# app/api/organizers/organizer/submissions.py
from uuid import UUID
from typing import Optional, Dict, Any, List
import csv
import io
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, or_
from pydantic import BaseModel

from app.core.db import get_db
from app.core.dependencies import require_current_organizer_admin
from app.services.submission.submission_service import SubmissionService

from app.models.event.event import Event
from app.models.submission.submission import Submission
from app.models.submission.submission_value import SubmissionValue
from app.models.event.event_field import EventField

from app.schemas.submission.submission_response import SubmissionResponse
from app.schemas.submission.submission_mapper import to_submission_response

router = APIRouter(
    prefix="/events/{event_uuid}/submissions",
    tags=["Organizer - Submissions"],
)

class BulkActionRequest(BaseModel):
    action: str # approve, reject, reopen, cancel
    submission_uuids: List[UUID]
    reason: Optional[str] = None

@router.get("", response_model=Dict[str, Any])
def list_event_submissions(
    event_uuid: UUID,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    membership=Depends(require_current_organizer_admin),
):
    """
    Organizer 後台 - 取得某活動的報名紀錄 (含 Server-side 篩選與搜尋)
    """
    event = db.query(Event).filter(Event.uuid == event_uuid, Event.organizer_uuid == membership.organizer_uuid).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    stats_query = (
        db.query(Submission.status, func.count(Submission.uuid))
        .filter(Submission.event_uuid == event_uuid, Submission.is_deleted == False)
        .group_by(Submission.status)
        .all()
    )
    stats = {s: count for s, count in stats_query}
    total_count = sum(stats.values())

    query = (
        db.query(Submission)
        .options(selectinload(Submission.values).selectinload(SubmissionValue.field))
        .filter(Submission.event_uuid == event_uuid, Submission.is_deleted == False)
    )

    if status and status != "all":
        query = query.filter(Submission.status == status)

    if search:
        search_filter = or_(
            Submission.user_email.ilike(f"%{search}%"),
            Submission.submission_code.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)

    total = query.count()
    submissions = query.order_by(Submission.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [to_submission_response(s) for s in submissions],
        "total": total,
        "page": page,
        "page_size": page_size,
        "summary": {
            "total": total_count,
            "status_counts": stats
        }
    }

@router.post("/bulk-action")
def bulk_action_submissions(
    event_uuid: UUID,
    req: BulkActionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    membership=Depends(require_current_organizer_admin),
):
    """
    批量操作 (Approve / Reject / Reopen / Cancel)
    """
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

    return SubmissionService.bulk_action(
        db=db,
        event_uuid=event_uuid,
        submission_uuids=req.submission_uuids,
        action=req.action,
        actor_id=membership.user_uuid,
        actor_role="organizer",
        reason=req.reason,
        background_tasks=background_tasks,
    )

@router.get("/export")
def export_event_submissions(
    event_uuid: UUID,
    db: Session = Depends(get_db),
    membership=Depends(require_current_organizer_admin),
):
    """
    匯出 CSV 報表 (Streaming 模式，防止 OOM)
    """
    event = db.query(Event).filter(Event.uuid == event_uuid, Event.organizer_uuid == membership.organizer_uuid).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    def generate_csv():
        # Header
        output = io.StringIO()
        writer = csv.writer(output)

        base_headers = ["Code", "Email", "Status", "Created At", "Notes"]
        event_fields = db.query(EventField).filter(EventField.event_uuid == event_uuid).order_by(EventField.order).all()
        field_keys = [f.field_key for f in event_fields]
        field_labels = [f.name for f in event_fields]

        writer.writerow(base_headers + field_labels)
        yield output.getvalue().encode("utf-8-sig")
        output.truncate(0)
        output.seek(0)

        # Content (Batch fetch to save memory if very large)
        submissions_query = (
            db.query(Submission)
            .options(selectinload(Submission.values).selectinload(SubmissionValue.field))
            .filter(Submission.event_uuid == event_uuid, Submission.is_deleted == False)
            .order_by(Submission.created_at.desc())
        )

        for s in submissions_query.yield_per(100):
            row = [
                s.submission_code,
                s.user_email,
                s.status.value if hasattr(s.status, "value") else s.status,
                s.created_at.isoformat(),
                s.notes or ""
            ]
            val_map = {v.field_key: v.value for v in s.values}
            for key in field_keys:
                row.append(val_map.get(key, ""))
            writer.writerow(row)
            yield output.getvalue().encode("utf-8-sig")
            output.truncate(0)
            output.seek(0)

    filename = f"submissions_{event.event_code}_{datetime.now().strftime('%Y%m%d%H%M')}.csv"
    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
