# app/schemas/event/field/event_field_create.py

from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Any, Literal


EventFieldType = Literal[
    "text",
    "textarea",
    "email",
    "tel",
    "number",
    "select",
    "radio",
    "checkbox",
    "date",
]


class EventFieldCreate(BaseModel):
    """
    Organizer creates a submission field for an event

    NOTE:
    - event_uuid comes from URL path
    - DO NOT include event_uuid in request body
    """

    field_key: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[a-z][a-z0-9_]*$",
    )
    label: str = Field(min_length=1, max_length=255)
    field_type: EventFieldType
    required: bool = False
    placeholder: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    options: Optional[List[Any]] = Field(default=None, max_length=100)
    validation: dict[str, Any] = Field(default_factory=dict)
    sort_order: int = Field(default=0, ge=0)
    is_enabled: bool = True

    @model_validator(mode="after")
    def selectable_fields_require_options(self):
        if self.field_type in {"select", "radio"} and not self.options:
            raise ValueError("select and radio fields require options")
        return self
