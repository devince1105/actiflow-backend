# app/schemas/event/organizer/event_list_item.py

from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional


class EventListItem(BaseModel):
    uuid: UUID
    event_code: str

    name: str
    status: str

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    submissions_count: int = 0

    model_config = {"from_attributes": True}
