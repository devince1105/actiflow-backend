from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AdminAuditLogListItem(BaseModel):
    uuid: UUID
    audit_code: str
    user_uuid: UUID | None = None
    user_email: str
    user_role: str | None = None
    action: str
    target_type: str | None = None
    target_uuid: UUID | None = None
    before_data: dict[str, Any] | None = None
    after_data: dict[str, Any] | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime


class AdminAuditLogListResponse(BaseModel):
    items: list[AdminAuditLogListItem]
    total: int
    page: int
    page_size: int
    pages: int
    action_counts: dict[str, int] = Field(default_factory=dict)
    target_types: list[str] = Field(default_factory=list)
