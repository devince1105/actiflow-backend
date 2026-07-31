# app/schemas/event/public/event_detail.py
# 給外部 / public

from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, ConfigDict

from app.schemas.event.category.event_category_public import (
    EventCategoryPublic,
)
from app.schemas.organizer.public.organizer_public import (
    OrganizerPublic,
)

# =====================================================
# Time
# =====================================================

class EventTimePublic(BaseModel):
    start: datetime
    end: Optional[datetime] = None
    display: str


# =====================================================
# Location
# =====================================================

class EventLocationPublic(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None


# =====================================================
# Event Content (Editor Blocks)
# =====================================================

class EventContentBlockPublic(BaseModel):
    id: Optional[str] = None
    type: str
    title: Optional[str] = None
    data: Any


class EventContentPublic(BaseModel):
    blocks: List[EventContentBlockPublic]


# =====================================================
# Public Event Detail
# =====================================================

class EventDetailPublic(BaseModel):
    uuid: str
    event_code: str
    name: str
    description: Optional[str] = None
    cover_image_url: Optional[str] = None

    category: Optional[EventCategoryPublic] = None
    time: EventTimePublic
    location: Optional[EventLocationPublic] = None
    organizer: Optional[OrganizerPublic] = None

    registration_deadline: Optional[datetime] = None

    # ✅ 活動內容（Editor blocks）
    content: Optional[EventContentPublic] = None

    # 容量控制
    max_capacity: int = 0
    current_attendance: int = 0

    # 其他未結構化資料
    extra: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)
