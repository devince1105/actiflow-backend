# app/api/events/system/event_read.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.db import get_db

from app.schemas.event.organizer.event_response import OrganizerEventResponse
from app.models.event.event import Event

router = APIRouter(
    prefix="/system/events",
    tags=["System Events"],
)


# ============================================================
# System Event Detail
# ============================================================
@router.get("/{event_uuid}", response_model=OrganizerEventResponse)
def get_system_event_detail(
    event_uuid: UUID,
    db: Session = Depends(get_db),
):
    """
    System / Internal Event Detail API

    - Use UUID
    - For system / admin / debug purpose
    - NOT for public frontend

    條件：
    - event 必須存在
    - is_active = True
    - is_deleted = False
    """

    event = (
        db.query(Event)
        .filter(
            Event.uuid == event_uuid,
            Event.is_active == True,
            Event.is_deleted == False,
        )
        .first()
    )

    if not event:
        raise HTTPException(
            status_code=404,
            detail="Event not found",
        )

    return OrganizerEventResponse.model_validate(event)
