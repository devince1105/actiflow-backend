from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AdminSubmissionListItem(BaseModel):
    uuid: UUID
    submission_code: str
    user_email: str
    submitted_by_email: str | None = None
    status: str
    status_reason: str | None = None
    event_uuid: UUID
    event_code: str
    event_name: str
    organizer_uuid: UUID
    organizer_name: str
    submitted_at: datetime


class AdminSubmissionListResponse(BaseModel):
    items: list[AdminSubmissionListItem]
    total: int
    page: int
    page_size: int
    pages: int
    status_counts: dict[str, int] = Field(default_factory=dict)
