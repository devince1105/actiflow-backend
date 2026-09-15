# app/schemas/event/organizer/event_status_update.py

from pydantic import BaseModel, Field
from typing import Literal


class OrganizerEventStatusUpdate(BaseModel):
    """
    Organizer 後台 Event 狀態變更（Command）

    僅允許狀態轉換，不處理其他欄位
    """

    status: Literal[
        "draft",
        "published",
        "closed",
    ] = Field(
        ...,
        description="Event status transition"
    )
