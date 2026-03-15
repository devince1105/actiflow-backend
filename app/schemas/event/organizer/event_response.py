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

    start_date: datetime
    end_date: Optional[datetime] = None
    registration_deadline: Optional[datetime] = None

    status: str

    config: Optional[Dict[str, Any]] = None

    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }
