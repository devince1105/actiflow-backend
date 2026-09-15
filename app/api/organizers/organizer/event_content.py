# app/api/organizers/organizer/event_content.py

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.dependencies import (
    require_current_organizer_admin,
    require_current_organizer_member,
)
from app.models.event.event import Event
from app.schemas.event.public.event_content import EventContentSchema
from app.crud.event.crud_event_content import (
    get_event_content as get_event_content_crud,
    replace_event_content as replace_event_content_crud,
    patch_event_content as patch_event_content_crud,
    delete_event_content as delete_event_content_crud,
)

router = APIRouter()


def _require_owned_event(db: Session, event_uuid: UUID, organizer_uuid: UUID) -> None:
    exists = (
        db.query(Event.uuid)
        .filter(
            Event.uuid == event_uuid,
            Event.organizer_uuid == organizer_uuid,
            Event.is_deleted == False,
        )
        .first()
    )
    if not exists:
        raise HTTPException(status_code=404, detail="Event not found")


@router.get(
    "/events/{event_uuid}/content",
    response_model=EventContentSchema,
)
def get_event_content(
    organizer_uuid: UUID,
    event_uuid: UUID,
    db: Session = Depends(get_db),
    membership=Depends(require_current_organizer_member),
):
    _require_owned_event(db, event_uuid, organizer_uuid)
    return get_event_content_crud(
        db,
        event_uuid=event_uuid,
    )


@router.put(
    "/events/{event_uuid}/content",
    response_model=EventContentSchema,
)
def replace_event_content(
    organizer_uuid: UUID,
    event_uuid: UUID,
    payload: EventContentSchema,
    db: Session = Depends(get_db),
    membership=Depends(require_current_organizer_admin),
):
    _require_owned_event(db, event_uuid, organizer_uuid)
    try:
        return replace_event_content_crud(
            db,
            event_uuid=event_uuid,
            content=payload.model_dump(),
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Event not found")


@router.patch(
    "/events/{event_uuid}/content",
    response_model=EventContentSchema,
)   
def patch_event_content(
    organizer_uuid: UUID,
    event_uuid: UUID,
    payload: EventContentSchema,
    db: Session = Depends(get_db),
    membership=Depends(require_current_organizer_admin),
):
    _require_owned_event(db, event_uuid, organizer_uuid)
    try:
        return patch_event_content_crud(
            db,
            event_uuid=event_uuid,
            content=payload.model_dump(),
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Event not found")
        

@router.delete(
    "/events/{event_uuid}/content",
    response_model=EventContentSchema,
)   
def delete_event_content(
    organizer_uuid: UUID,
    event_uuid: UUID,
    db: Session = Depends(get_db),
    membership=Depends(require_current_organizer_admin),
):
    _require_owned_event(db, event_uuid, organizer_uuid)
    try:
        return delete_event_content_crud(
            db,
            event_uuid=event_uuid,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Event not found")
