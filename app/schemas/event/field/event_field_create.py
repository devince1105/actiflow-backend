# app/schemas/event/field/event_field_create.py

from pydantic import BaseModel
from typing import Optional, List, Any
from uuid import UUID


class EventFieldCreate(BaseModel):
    """
    Organizer creates a submission field for an event

    NOTE:
    - event_uuid comes from URL path
    - DO NOT include event_uuid in request body
    """

    field_key: str
    label: str
    field_type: str           # e.g. text / select / checkbox
    required: bool = False
    options: Optional[List[Any]] = None
    sort_order: int = 0
