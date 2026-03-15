# app/api/organizers/organizer/events.py

"""
Organizer 後台 - Event CRUD（owner / admin）
Canonical Organizer API

Mounted at:
    /organizers/{organizer_uuid}/events

This file uses:
- membership = require_current_organizer_admin
- membership.organizer_uuid / membership.user_uuid / membership.role
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.dependencies import require_current_organizer_admin

from app.core.constants.event_status import EventStatus
from app.core.domain.event_status_guard import assert_event_status_transition

from app.schemas.event.organizer.event_create import OrganizerEventCreate
from app.schemas.event.organizer.event_update import OrganizerEventUpdate
from app.schemas.event.organizer.event_response import OrganizerEventResponse
from app.schemas.common.pagination import PaginatedResponse

from app.crud.event.crud_event import (
    create_event_by_organizer,
    update_event_by_organizer,
    list_events_by_organizer,
    get_event_by_uuid,
    soft_delete_event_by_organizer,
    update_event_status_by_organizer,
)

from app.models.event.event import Event
from app.api.utils.slug import generate_slug


router = APIRouter(
    prefix="/events",
    tags=["Organizer - Events"],
)


# -------------------------------------------------------------------
# List events
# GET /organizers/{organizer_uuid}/events?page=1&page_size=20
# -------------------------------------------------------------------
@router.get("", response_model=PaginatedResponse[OrganizerEventResponse])
def list_events(
    organizer_uuid: UUID,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    membership=Depends(require_current_organizer_admin),
):
    if membership.organizer_uuid != organizer_uuid:
        raise HTTPException(status_code=403, detail="Organizer mismatch")

    # Base query (no order_by yet)
    base_query = (
        db.query(Event)
        .filter(
            Event.organizer_uuid == organizer_uuid,
            Event.is_deleted == False,
        )
    )

    # ---- total count (no order_by for performance) ----
    total = base_query.count()

    # ---- paginated result ----
    events = (
        base_query
        .order_by(Event.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaginatedResponse(
        items=[OrganizerEventResponse.model_validate(e) for e in events],
        total=total,
        page=page,
        page_size=page_size,
    )

# -------------------------------------------------------------------
# Get event detail
# GET /organizers/{organizer_uuid}/events/{event_uuid}
# -------------------------------------------------------------------
@router.get("/{event_uuid}", response_model=OrganizerEventResponse)
def get_event_detail(
    organizer_uuid: UUID,
    event_uuid: UUID,
    db: Session = Depends(get_db),
    membership=Depends(require_current_organizer_admin),
):
    if membership.organizer_uuid != organizer_uuid:
        raise HTTPException(status_code=403, detail="Organizer mismatch")

    event = _get_event_or_404(db, event_uuid, organizer_uuid)
    return OrganizerEventResponse.model_validate(event)


# -------------------------------------------------------------------
# Create event
# POST /organizers/{organizer_uuid}/events
# -------------------------------------------------------------------
@router.post("", response_model=OrganizerEventResponse)
def create_event(
    organizer_uuid: UUID,
    data: OrganizerEventCreate,
    db: Session = Depends(get_db),
    membership=Depends(require_current_organizer_admin),
):
    if membership.organizer_uuid != organizer_uuid:
        raise HTTPException(status_code=403, detail="Organizer mismatch")

    payload = data.model_dump(exclude_none=True, exclude={"status"})

    # ---- normalize title/name (MVP compatibility) ----
    title = payload.pop("title", None)
    if title is not None and "name" not in payload:
        payload["name"] = title

    # ---- normalize dates (MVP compatibility) ----
    event_start_at = payload.pop("event_start_at", None)
    if event_start_at is not None and "start_date" not in payload:
        payload["start_date"] = event_start_at

    event_end_at = payload.pop("event_end_at", None)
    if event_end_at is not None and "end_date" not in payload:
        payload["end_date"] = event_end_at

    registration_end_at = payload.pop("registration_end_at", None)
    if registration_end_at is not None and "registration_deadline" not in payload:
        payload["registration_deadline"] = registration_end_at

    # registration_start_at：放進 config（你目前 schema 沒有對應 DB 欄位）
    registration_start_at = payload.pop("registration_start_at", None)
    if registration_start_at is not None:
        merged_config = dict(payload.get("config") or {})
        if isinstance(registration_start_at, datetime):
            merged_config["registration_start_at"] = registration_start_at.isoformat()
        else:
            merged_config["registration_start_at"] = registration_start_at
        payload["config"] = merged_config

    # ---- Generate event code once ----
    ev_code = generate_event_code()

    # ---- Ensure slug is present and NOT NULL ----
    name_for_slug = payload.get("name")
    slug = generate_slug(name_for_slug) if name_for_slug else None
    payload["slug"] = slug or ev_code  # fallback ensures non-null

    event = Event(
        **payload,
        organizer_uuid=organizer_uuid,
        event_code=ev_code,
        status=EventStatus.DRAFT,
        created_by=membership.user_uuid,
        created_by_role=membership.role,
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    return OrganizerEventResponse.model_validate(event)


# -------------------------------------------------------------------
# Update event
# PATCH /organizers/{organizer_uuid}/events/{event_uuid}  ✅ (partial update)
# PUT   /organizers/{organizer_uuid}/events/{event_uuid}  ✅ (accept same behavior for MVP)
# -------------------------------------------------------------------
@router.patch("/{event_uuid}", response_model=OrganizerEventResponse)
@router.put("/{event_uuid}", response_model=OrganizerEventResponse)
def update_event(
    organizer_uuid: UUID,
    event_uuid: UUID,
    data: OrganizerEventUpdate,
    db: Session = Depends(get_db),
    membership=Depends(require_current_organizer_admin),
):
    if membership.organizer_uuid != organizer_uuid:
        raise HTTPException(status_code=403, detail="Organizer mismatch")

    event = _get_event_or_404(db, event_uuid, organizer_uuid)

    # Only update provided fields
    update_data = data.model_dump(exclude_unset=True, exclude_none=True)

    # ---- Disallow status changes here (use publish/unpublish/close endpoints) ----
    if "status" in update_data:
        raise HTTPException(
            status_code=400,
            detail="Event status must be changed via publish/unpublish/close APIs",
        )

    # ---- normalize title/name (MVP compatibility) ----
    title = update_data.pop("title", None)
    if title is not None and "name" not in update_data:
        update_data["name"] = title

    # ---- normalize dates (MVP compatibility) ----
    event_start_at = update_data.pop("event_start_at", None)
    if event_start_at is not None and "start_date" not in update_data:
        update_data["start_date"] = event_start_at

    event_end_at = update_data.pop("event_end_at", None)
    if event_end_at is not None and "end_date" not in update_data:
        update_data["end_date"] = event_end_at

    registration_end_at = update_data.pop("registration_end_at", None)
    if registration_end_at is not None and "registration_deadline" not in update_data:
        update_data["registration_deadline"] = registration_end_at

    # registration_start_at：merge into config
    registration_start_at = update_data.pop("registration_start_at", None)
    if registration_start_at is not None:
        merged_config = dict(event.config or {})
        incoming_config = update_data.pop("config", None)
        if isinstance(incoming_config, dict):
            merged_config.update(incoming_config)

        if isinstance(registration_start_at, datetime):
            merged_config["registration_start_at"] = registration_start_at.isoformat()
        else:
            merged_config["registration_start_at"] = registration_start_at

        update_data["config"] = merged_config
    elif "config" in update_data:
        merged_config = dict(event.config or {})
        incoming_config = update_data.get("config") or {}
        if isinstance(incoming_config, dict):
            merged_config.update(incoming_config)
            update_data["config"] = merged_config

    # If name changed => regenerate slug (never set slug to None)
    if "name" in update_data and update_data["name"]:
        update_data["slug"] = generate_slug(update_data["name"]) or event.slug

    # Apply updates
    for field, value in update_data.items():
        setattr(event, field, value)

    event.updated_by = membership.user_uuid
    event.updated_by_role = membership.role

    db.commit()
    db.refresh(event)

    return OrganizerEventResponse.model_validate(event)


# -------------------------------------------------------------------
# Delete event
# DELETE /organizers/{organizer_uuid}/events/{event_uuid}
# -------------------------------------------------------------------
@router.delete("/{event_uuid}", status_code=204)
def delete_event(
    organizer_uuid: UUID,
    event_uuid: UUID,
    db: Session = Depends(get_db),
    membership=Depends(require_current_organizer_admin),
):
    if membership.organizer_uuid != organizer_uuid:
        raise HTTPException(403, "Organizer mismatch")

    event = soft_delete_event_by_organizer(
        db=db,
        event_uuid=event_uuid,
        deleter_uuid=membership.user_uuid,
        deleter_role=membership.role,
    )

    if not event or event.organizer_uuid != organizer_uuid:
        raise HTTPException(404, "Event not found")

    return

# -------------------------------------------------------------------
# Publish event (draft -> published)
# PATCH /organizers/{organizer_uuid}/events/{event_uuid}/publish
# -------------------------------------------------------------------
@router.patch("/{event_uuid}/publish", response_model=OrganizerEventResponse)
def publish_event(
    organizer_uuid: UUID,
    event_uuid: UUID,
    db: Session = Depends(get_db),
    membership=Depends(require_current_organizer_admin),
):
    if membership.organizer_uuid != organizer_uuid:
        raise HTTPException(status_code=403, detail="Organizer mismatch")

    event = _get_event_or_404(db, event_uuid, organizer_uuid)

    assert_event_status_transition(
        current=EventStatus(event.status),
        target=EventStatus.PUBLISHED,
    )

    event.status = EventStatus.PUBLISHED
    event.updated_by = membership.user_uuid
    event.updated_by_role = membership.role

    db.commit()
    db.refresh(event)

    return OrganizerEventResponse.model_validate(event)


# -------------------------------------------------------------------
# Unpublish event (published -> draft)
# PATCH /organizers/{organizer_uuid}/events/{event_uuid}/unpublish
# -------------------------------------------------------------------
@router.patch("/{event_uuid}/unpublish", response_model=OrganizerEventResponse)
def unpublish_event(
    organizer_uuid: UUID,
    event_uuid: UUID,
    db: Session = Depends(get_db),
    membership=Depends(require_current_organizer_admin),
):
    if membership.organizer_uuid != organizer_uuid:
        raise HTTPException(status_code=403, detail="Organizer mismatch")

    event = _get_event_or_404(db, event_uuid, organizer_uuid)

    assert_event_status_transition(
        current=EventStatus(event.status),
        target=EventStatus.DRAFT,
    )

    event.status = EventStatus.DRAFT
    event.updated_by = membership.user_uuid
    event.updated_by_role = membership.role

    db.commit()
    db.refresh(event)

    return OrganizerEventResponse.model_validate(event)


# -------------------------------------------------------------------
# Close event (published -> closed)
# PATCH /organizers/{organizer_uuid}/events/{event_uuid}/close
# -------------------------------------------------------------------
@router.patch("/{event_uuid}/close", response_model=OrganizerEventResponse)
def close_event(
    organizer_uuid: UUID,
    event_uuid: UUID,
    db: Session = Depends(get_db),
    membership=Depends(require_current_organizer_admin),
):
    if membership.organizer_uuid != organizer_uuid:
        raise HTTPException(status_code=403, detail="Organizer mismatch")

    event = _get_event_or_404(db, event_uuid, organizer_uuid)

    assert_event_status_transition(
        current=EventStatus(event.status),
        target=EventStatus.CLOSED,
    )

    event.status = EventStatus.CLOSED
    event.updated_by = membership.user_uuid
    event.updated_by_role = membership.role

    db.commit()
    db.refresh(event)

    return OrganizerEventResponse.model_validate(event)


# -------------------------------------------------------------------
# Utilities
# -------------------------------------------------------------------
def generate_event_code() -> str:
    """例：EVT-20260105123045"""
    return f"EVT-{datetime.utcnow():%Y%m%d%H%M%S}"


def _get_event_or_404(
    db: Session,
    event_uuid: UUID,
    organizer_uuid: UUID,
) -> Event:
    event = (
        db.query(Event)
        .filter(
            Event.uuid == event_uuid,
            Event.organizer_uuid == organizer_uuid,
            Event.is_deleted == False,
        )
        .first()
    )

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return event
