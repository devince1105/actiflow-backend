# app/schemas/event/field/event_field_update.py

from pydantic import BaseModel, Field
from typing import Optional, List, Any

from app.schemas.event.field.event_field_create import EventFieldType


class EventFieldUpdate(BaseModel):
    """
    更新 EventField 用 Schema。
    event_uuid 與 field_key 不能修改。
    """

    label: Optional[str] = Field(default=None, min_length=1, max_length=255)
    field_type: Optional[EventFieldType] = None
    required: Optional[bool] = None
    placeholder: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    options: Optional[List[Any]] = Field(default=None, max_length=100)
    validation: Optional[dict[str, Any]] = None
    sort_order: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None
    is_enabled: Optional[bool] = None
