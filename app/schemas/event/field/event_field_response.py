# app/schemas/event/field/event_field_response.py

from uuid import UUID
from typing import Optional, List, Any
from pydantic import BaseModel, field_validator

from app.schemas.event.field.event_field_create import EventFieldType


class EventFieldResponse(BaseModel):
    uuid: UUID
    field_key: str
    label: str
    placeholder: Optional[str] = None
    description: Optional[str] = None
    field_type: EventFieldType
    required: bool
    is_active: bool
    is_enabled: bool
    options: Optional[List[Any]] = None
    validation: dict[str, Any]
    sort_order: int

    @field_validator("options", mode="before")
    @classmethod
    def normalize_options(cls, v):
        """
        DB 中 options 可能是 {}（JSONB 預設）
        Response 統一轉為 list
        """
        if v is None:
            return None
        if isinstance(v, dict):
            return []
        return v

    model_config = {"from_attributes": True}
