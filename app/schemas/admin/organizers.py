from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AdminOrganizerListItem(BaseModel):
    uuid: UUID
    name: str
    email: str | None = None
    status: str
    is_active: bool
    members_count: int = 0
    events_count: int = 0
    created_at: datetime


class AdminOrganizerListResponse(BaseModel):
    items: list[AdminOrganizerListItem]
    total: int


class AdminOrganizerApplicationItem(BaseModel):
    uuid: UUID
    user_uuid: UUID
    applicant_email: str
    organization_name: str
    application_data: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = None
    status: str
    submitted_at: datetime
    reviewed_at: datetime | None = None


class AdminOrganizerApplicationListResponse(BaseModel):
    items: list[AdminOrganizerApplicationItem]
    total: int


class AdminOrganizerApplicationReview(BaseModel):
    reason: str | None = Field(default=None, max_length=500)
