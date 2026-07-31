# app/schemas/event/organizer/event_response.py

from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any


class OrganizerEventResponse(BaseModel):
    """
    Organizer 後台 Event 詳細資料（Read / Create / Update Response）
    """

    uuid: UUID
    event_code: str
    organizer_uuid: UUID

    name: str
    description: Optional[str] = None
    event_category_uuid: UUID
    location: Optional[str] = None
    max_capacity: int

    start_date: datetime
    end_date: Optional[datetime] = None
    registration_deadline: Optional[datetime] = None
    submitted_for_review_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    review_reason: Optional[str] = None

    status: str

    config: Optional[Dict[str, Any]] = None
    cover_image_url: Optional[str] = None

    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }
