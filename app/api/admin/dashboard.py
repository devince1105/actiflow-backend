from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.core.constants.event_status import EventStatus
from app.core.db import get_db
from app.core.dependencies import require_super_admin
from app.models.event.event import Event
from app.models.organizer.organizer import Organizer
from app.models.organizer.organizer_application import OrganizerApplication
from app.models.submission.submission import Submission
from app.models.user.user import User
from app.schemas.admin.dashboard import (
    AdminDashboardResponse,
    AdminEventStats,
)


router = APIRouter(
    prefix="/admin/dashboard",
    tags=["Admin - Dashboard"],
)


@router.get("", response_model=AdminDashboardResponse)
def get_admin_dashboard(
    db: Session = Depends(get_db),
    _admin=Depends(require_super_admin),
):
    now = datetime.now()
    active_event_filters = (
        Event.is_deleted == False,
        Event.is_active == True,
    )
    upcoming_filter = or_(
        Event.end_date >= now,
        and_(Event.end_date.is_(None), Event.start_date >= now),
    )
    past_filter = or_(
        Event.end_date < now,
        and_(Event.end_date.is_(None), Event.start_date < now),
    )

    event_status_counts = dict(
        db.query(Event.status, func.count(Event.id))
        .filter(*active_event_filters)
        .group_by(Event.status)
        .all()
    )

    return AdminDashboardResponse(
        users_total=db.query(func.count(User.id))
        .filter(User.is_deleted == False, User.is_active == True)
        .scalar()
        or 0,
        organizers_total=db.query(func.count(Organizer.id))
        .filter(Organizer.is_deleted == False, Organizer.is_active == True)
        .scalar()
        or 0,
        pending_organizer_applications=db.query(
            func.count(OrganizerApplication.id)
        )
        .filter(
            OrganizerApplication.status == "pending",
            OrganizerApplication.is_deleted == False,
            OrganizerApplication.is_active == True,
        )
        .scalar()
        or 0,
        submissions_total=db.query(func.count(Submission.id))
        .filter(
            Submission.is_deleted == False,
            Submission.is_active == True,
        )
        .scalar()
        or 0,
        events=AdminEventStats(
            total=sum(event_status_counts.values()),
            draft=event_status_counts.get(EventStatus.DRAFT, 0),
            published=event_status_counts.get(EventStatus.PUBLISHED, 0),
            closed=event_status_counts.get(EventStatus.CLOSED, 0),
            upcoming=db.query(func.count(Event.id))
            .filter(
                *active_event_filters,
                Event.status == EventStatus.PUBLISHED,
                upcoming_filter,
            )
            .scalar()
            or 0,
            past=db.query(func.count(Event.id))
            .filter(
                *active_event_filters,
                Event.status == EventStatus.PUBLISHED,
                past_filter,
            )
            .scalar()
            or 0,
        ),
    )
