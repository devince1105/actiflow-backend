# app/schemas/event/category/event_category_base.py

from pydantic import BaseModel
from uuid import UUID


class EventCategoryBase(BaseModel):
    uuid: UUID
    code: str
    slug: str
    label_zh: str
    label_en: str
    color: str
    sort_order: int

    class Config:
        from_attributes = True
