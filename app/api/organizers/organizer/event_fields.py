# app/api/organizers/organizer/event_fields.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.db import get_db
from app.core.dependencies import require_current_organizer_admin
from app.crud.event.crud_event_field import event_field_crud
from app.schemas.event.field.event_field_create import EventFieldCreate
from app.schemas.event.field.event_field_update import EventFieldUpdate
from app.schemas.event.field.event_field_response import EventFieldResponse


router = APIRouter(
    prefix="/events/{event_uuid}/fields",
    tags=["Organizer - Event Fields"],
)

# ---------------------------------------------------------
# List
# ---------------------------------------------------------
@router.get("", response_model=list[EventFieldResponse])
def list_event_fields(
    event_uuid: UUID,
    db: Session = Depends(get_db),
    membership=Depends(require_current_organizer_admin),
):
    fields = event_field_crud.list_by_event(db, event_uuid)
    return [EventFieldResponse.model_validate(f) for f in fields]


# ---------------------------------------------------------
# Create
# ---------------------------------------------------------
@router.post("", response_model=EventFieldResponse)
def create_event_field(
    event_uuid: UUID,
    data: EventFieldCreate,
    db: Session = Depends(get_db),
    membership=Depends(require_current_organizer_admin),
):
    field = event_field_crud.create(
        db,
        event_uuid=event_uuid,
        data=data,
        created_by=membership.user_uuid,
        created_by_role=membership.role,
    )
    return EventFieldResponse.model_validate(field)


# ---------------------------------------------------------
# Update
# ---------------------------------------------------------
@router.patch("/{field_uuid}", response_model=EventFieldResponse)
def update_event_field(
    event_uuid: UUID,
    field_uuid: UUID,
    data: EventFieldUpdate,
    db: Session = Depends(get_db),
    membership=Depends(require_current_organizer_admin),
):
    field = event_field_crud.get_by_uuid(db, uuid=field_uuid)

    if not field or field.event_uuid != event_uuid:
        raise HTTPException(404, "EventField not found")

    field = event_field_crud.update(
        db,
        db_obj=field,
        data=data,
    )

    return EventFieldResponse.model_validate(field)
