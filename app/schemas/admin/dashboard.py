from pydantic import BaseModel


class AdminEventStats(BaseModel):
    total: int
    draft: int
    published: int
    closed: int
    upcoming: int
    past: int


class AdminDashboardResponse(BaseModel):
    users_total: int
    organizers_total: int
    pending_organizer_applications: int
    submissions_total: int
    events: AdminEventStats
