# app/schemas/event/category/event_category_base.py

from pydantic import BaseModel, ConfigDict
from uuid import UUID


class EventCategoryBase(BaseModel):
    uuid: UUID
    code: str
    slug: str
    label_zh: str
    label_en: str
    color: str
    sort_order: int

    model_config = ConfigDict(from_attributes=True)
