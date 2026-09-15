from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AdminUserListItem(BaseModel):
    uuid: UUID
    email: str
    avatar_url: str | None = None
    is_active: bool
    is_email_verified: bool
    system_roles: list[str] = Field(default_factory=list)
    organizer_memberships_count: int = 0
    submissions_count: int = 0
    created_at: datetime


class AdminUserListResponse(BaseModel):
    items: list[AdminUserListItem]
    total: int
    page: int
    page_size: int
    pages: int
