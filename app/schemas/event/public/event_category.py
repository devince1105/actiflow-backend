# app/schemas/event/public/event_category.py

from typing import List, Optional
from pydantic import BaseModel, Field


class PublicEventCategory(BaseModel):
    """
    Public Event Category
    - 來源：Event.config["category"]
    - 用於活動列表分類 Tabs
    """

    code: str = Field(..., description="Category code (internal identifier)")
    slug: str = Field(..., description="URL-friendly slug")
    label: str = Field(..., description="Display label")
    color: Optional[str] = Field(
        None, description="UI color hint (e.g. INDIGO, BLUE)"
    )
    icon: Optional[str] = Field(
        None, description="Icon name (e.g. camera, mountain)"
    )

    model_config = {
        "from_attributes": True
    }


class PublicEventCategoryListResponse(BaseModel):
    """
    Public Event Category List Response
    """

    items: List[PublicEventCategory]
