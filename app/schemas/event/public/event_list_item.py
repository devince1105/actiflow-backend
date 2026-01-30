# app/schemas/event/public/event_list_item.py

from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.event.public.event_category import PublicEventCategory
from app.schemas.organizer.public.organizer_public import OrganizerPublic

if TYPE_CHECKING:
    from app.models.event.event import Event


# ============================================================
# Time display
# ============================================================
class EventPublicTime(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    display: Optional[str] = None


# ============================================================
# Location
# ============================================================
class EventPublicLocation(BaseModel):
    uuid: Optional[UUID] = None
    name: Optional[str] = None
    address: Optional[str] = None


# ============================================================
# Config（⚠️ 不再繼承 BaseSchema）
# ============================================================
class EventPublicConfig(BaseModel):
    category: Optional[PublicEventCategory] = None


# ============================================================
# Public Event List Item
# ============================================================
class EventPublicListItem(BaseModel):
    uuid: UUID
    event_code: str

    name: str
    description: Optional[str] = None
    cover_image_url: Optional[str] = None

    time: Optional[EventPublicTime] = None
    location: Optional[EventPublicLocation] = None
    organizer: Optional[OrganizerPublic] = None
    config: Optional[EventPublicConfig] = None
    
    # Capacity
    capacity: Optional[int] = None
    registered_count: int = 0

    model_config = ConfigDict(from_attributes=True)
