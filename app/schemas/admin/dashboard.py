from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AdminEventStats(BaseModel):
    total: int
    draft: int
    pending_review: int
    changes_requested: int
    published: int
    closed: int
    upcoming: int
    past: int


class AdminDashboardAuditItem(BaseModel):
    uuid: UUID
    audit_code: str
    user_email: str
    action: str
    target_type: str | None = None
    target_uuid: UUID | None = None
    timestamp: datetime


class AdminDashboardResponse(BaseModel):
    users_total: int
    organizers_total: int
    pending_organizer_applications: int
    pending_submissions: int
    unverified_users: int
    submissions_total: int
    events: AdminEventStats
    recent_audit_logs: list[AdminDashboardAuditItem]
