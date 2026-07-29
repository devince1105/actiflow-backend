# app/api/router.py

from fastapi import APIRouter

# =======================
# Auth
# =======================
from app.api.auth.login import router as login_router
from app.api.auth.refresh import router as refresh_router
from app.api.auth.me import router as auth_me_router
from app.api.auth.logout import router as logout_router

# =======================
# Email (Public)
# =======================
from app.api.email.public import router as email_public_router
from app.api.email.resend import router as email_resend_router

# =======================
# Public - Events (✅ 正確寫法)
# =======================
from app.api.events.public import events as public_events_module
from app.api.events.public import event_categories as public_event_categories_module
from app.api.events.public import event_detail as public_event_detail_module
from app.api.events.public import event_read as public_event_view_module

# Public - Submissions (✅ 正確寫法)
from app.api.events.public.submissions import router as public_submissions_router


# =======================
# Users
# =======================
from app.api.users.me.me import router as users_me_router
from app.api.users.me.submissions import router as users_me_submissions_router
from app.api.users.me.participations import router as users_me_participations_router
from app.api.uploads.images import router as image_uploads_router

# =======================
# Organizers (Public)
# =======================
from app.api.organizers.public.organizers import (
    router as public_organizers_router,
)

# =======================
# Organizers (Organizer scope)
# =======================
from app.api.organizers.organizer.dashboard import (
    router as organizer_dashboard_router,
)

from app.api.organizers.organizer.events import (
    router as organizer_events_router,
)
from app.api.organizers.organizer.event_fields import (
    router as organizer_event_fields_router,
)
from app.api.organizers.organizer.event_content import(
    router as event_content_router
)
from app.api.organizers.organizer.submissions import (
    router as organizer_submissions_router,
)
from app.api.organizers.organizer.members import (
    router as organizer_members_router,
)
from app.api.organizers.organizer.applications import (
    router as organizer_applications_router,
)
from app.api.organizers.organizer.profile import (
    router as organizer_profile_router,
)
from app.api.organizers.organizer.activity_templates import (
    router as organizer_activity_templates_router,
)


# =======================
# Organizers (Admin scope)
# =======================
from app.api.organizers.admin.organizers import (
    router as admin_organizers_router,
)
from app.api.organizers.admin.organizer_members import (
    router as admin_organizer_members_router,
)
from app.api.organizers.admin.organizer_applications import (
    router as admin_organizer_applications_router,
)

# =======================
# System
# =======================
from app.api.system.health import router as system_health_router
from app.api.system.me import router as system_me_router
from app.api.system.memberships import router as system_memberships_router
from app.api.system.permissions import router as system_permissions_router
from app.api.system.settings import router as system_settings_router
from app.api.system.organizer_approval import (
    router as organizer_approval_router,
)
from app.api.admin.dashboard import router as admin_dashboard_router
from app.api.admin.users_v2 import router as admin_users_router
from app.api.admin.organizers_v2 import router as admin_organizers_v2_router

# ============================================================
# Root API Router
# ============================================================
api_router = APIRouter()

# ------------------------------------------------------------
# Auth
# ------------------------------------------------------------
api_router.include_router(login_router, prefix="/auth", tags=["Auth"])
api_router.include_router(refresh_router, prefix="/auth", tags=["Auth"])
api_router.include_router(auth_me_router, prefix="/auth", tags=["Auth"])
api_router.include_router(logout_router, prefix="/auth", tags=["Auth"])

# ------------------------------------------------------------
# Public - Email
# ------------------------------------------------------------
api_router.include_router(
    email_public_router,
    prefix="/public/email",
    tags=["Public - Email"],
)
api_router.include_router(
    email_resend_router,
    prefix="/public/email",
    tags=["Public - Email"],
)

# ------------------------------------------------------------
# Public - Organizers
# ------------------------------------------------------------
api_router.include_router(
    public_organizers_router,
    prefix="/public/organizers",
    tags=["Public - Organizers"],
)

# ------------------------------------------------------------
# Public - Events  ✅（重點）
# ------------------------------------------------------------
# ⚠️ prefix 已經在 events.py / event_categories.py 裡定義
api_router.include_router(
    public_events_module.router,
    tags=["Public - Events"],
)

api_router.include_router(
    public_event_categories_module.router,
    tags=["Public - Event Categories"],
)

api_router.include_router(
    public_event_detail_module.router,
    tags=["Public - Event Detail"],
)

api_router.include_router(
    public_event_view_module.router,
    tags=["Public - Event View"],
)


# ------------------------------------------------------------
# Public - Submissions
# ------------------------------------------------------------
api_router.include_router(
    public_submissions_router,
    tags=["Public - Submissions"],
)

# ------------------------------------------------------------
# Users
# ------------------------------------------------------------
api_router.include_router(
    users_me_router,
    tags=["Users - Me"],
)
api_router.include_router(
    users_me_submissions_router,
    tags=["Users - Me - Submissions"],
)
api_router.include_router(
    users_me_participations_router,
    tags=["Users - Me - Participations"],
)
api_router.include_router(image_uploads_router)

# ------------------------------------------------------------
# Organizer scope
# ------------------------------------------------------------
api_router.include_router(
    organizer_dashboard_router,
    prefix="/organizers/{organizer_uuid}",
    tags=["Organizer - Dashboard"],
)

api_router.include_router(
    organizer_events_router,
    prefix="/organizers/{organizer_uuid}",
    tags=["Organizer - Events"],
)

api_router.include_router(
    organizer_event_fields_router,
    prefix="/organizers/{organizer_uuid}",
    tags=["Organizer - Event Fields"],
)

api_router.include_router(
    event_content_router,
    prefix="/organizers/{organizer_uuid}",
    tags=["Organizer - Event Content"],
)
api_router.include_router(
    organizer_submissions_router,
    prefix="/organizers/{organizer_uuid}",
    tags=["Organizer - Submissions"],
)

api_router.include_router(
    organizer_members_router,
    prefix="/organizers/{organizer_uuid}",
    tags=["Organizer - Members"],
)

api_router.include_router(
    organizer_activity_templates_router,
    prefix="/organizers/{organizer_uuid}",
    tags=["Organizer - Activity Templates"],
)

api_router.include_router(
    organizer_applications_router,
    prefix="/organizers/{organizer_uuid}",
    tags=["Organizer - Applications"],
)

api_router.include_router(
    organizer_profile_router,
    prefix="/organizers/{organizer_uuid}",
    tags=["Organizer - Profile"],
)

# ------------------------------------------------------------
# Admin scope
# ------------------------------------------------------------
api_router.include_router(admin_dashboard_router)
api_router.include_router(admin_users_router)
api_router.include_router(admin_organizers_v2_router)

api_router.include_router(
    admin_organizers_router,
    prefix="/admin/organizers",
    tags=["Admin - Organizers"],
)

api_router.include_router(
    admin_organizer_members_router,
    prefix="/admin/organizers",
    tags=["Admin - Organizers"],
)

api_router.include_router(
    admin_organizer_applications_router,
    prefix="/admin/organizers",
    tags=["Admin - Organizers"],
)

# ------------------------------------------------------------
# System
# ------------------------------------------------------------
api_router.include_router(
    system_health_router,
    prefix="/system",
    tags=["System"],
)

api_router.include_router(
    system_me_router,
    prefix="/system",
    tags=["System"],
)

api_router.include_router(
    system_memberships_router,
    prefix="/system",
    tags=["System"],
)

api_router.include_router(
    system_permissions_router,
    prefix="/system",
    tags=["System"],
)

api_router.include_router(
    system_settings_router,
    prefix="/system",
    tags=["System"],
)

api_router.include_router(
    organizer_approval_router,
    prefix="/system/organizer-approval",
    tags=["System - Organizer Approval"],
)
