from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AdminEventListItem(BaseModel):
    uuid: UUID
    event_code: str
    name: str
    organizer_uuid: UUID
    organizer_name: str
    status: str
    is_active: bool
    start_date: datetime
    end_date: datetime | None = None
    registration_deadline: datetime | None = None
    max_capacity: int
    current_attendance: int
    submissions_count: int
    submitted_for_review_at: datetime | None = None
    reviewed_at: datetime | None = None
    review_reason: str | None = None


class AdminEventListResponse(BaseModel):
    items: list[AdminEventListItem]
    total: int
    page: int
    page_size: int
    pages: int


class AdminEventModerationRequest(BaseModel):
    status: Literal["published", "closed"]
    reason: str = Field(min_length=3, max_length=500)


class AdminEventReviewRequest(BaseModel):
    decision: Literal["approve", "reject"]
    reason: str | None = Field(default=None, max_length=1000)
