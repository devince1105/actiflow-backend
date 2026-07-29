# app/core/dependencies.py

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from starlette import status

from app.core.db import get_db
from app.api.auth.dependencies import get_current_user, get_current_user_uuid
from app.models.membership.organizer_membership import OrganizerMembership
from app.models.user.user import User
from app.core.roles import (
    ACTIVE_ORGANIZER_ROLES,
    ORGANIZER_MANAGEMENT_ROLES,
    ORGANIZER_OWNER,
    SYSTEM_SUPER_ADMIN,
)

# ============================================================
# Legacy super admin guard (temporary)
# ============================================================

def require_super_admin(
    user=Depends(get_current_user),
):
    """
    ⚠️ Legacy guard
    Temporary compatibility for old APIs.

    TODO: remove after legacy APIs migrated.
    """

    memberships = user.get("memberships", []) if isinstance(user, dict) else []
    system_roles = [
        membership
        for membership in memberships
        if membership.get("type") == "system"
    ]

    if not any(m.get("role") == SYSTEM_SUPER_ADMIN for m in system_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required",
        )

    return user


# ============================================================
# Legacy organizer guard (TOKEN-BASED)
# ============================================================
# 適用於：
#   /organizer/events/*
#   /organizer/events/{event_uuid}
#
# organizer context 來自 token / identity
# ------------------------------------------------------------

def require_organizer_admin(
    user=Depends(get_current_user),
):
    """
    Legacy Organizer Admin guard

    ⚠️ organizer context 來自 token
    ⚠️ 不吃 organizer_uuid path / query
    """

    membership = getattr(user, "membership", None)

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organizer access required",
        )

    if membership.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organizer admin access required",
        )

    return membership


# ============================================================
# Canonical organizer context resolver (PATH-BASED)
# ============================================================
# 適用於：
#   /organizers/{organizer_uuid}/events/*
#   /organizers/{organizer_uuid}/events/{event_uuid}/*
# ------------------------------------------------------------

def resolve_current_organizer_context(
    organizer_uuid: UUID,
    db: Session = Depends(get_db),
    user_uuid: str = Depends(get_current_user_uuid),
):
    """
    Resolve organizer membership from DB (canonical)

    設計原則：
    - 不信任 token 內的 organizer 資訊
    - 以 path organizer_uuid + DB membership 為準
    """

    membership = (
        db.query(OrganizerMembership)
        .join(User, User.uuid == OrganizerMembership.user_uuid)
        .filter(
            OrganizerMembership.user_uuid == user_uuid,
            OrganizerMembership.organizer_uuid == organizer_uuid,
            OrganizerMembership.is_active == True,
            OrganizerMembership.is_deleted == False,
            OrganizerMembership.is_suspended == False,
            OrganizerMembership.role.in_(ACTIVE_ORGANIZER_ROLES),
            User.is_active == True,
            User.is_deleted == False,
        )
        .first()
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organizer access required",
        )

    return membership


# ============================================================
# Canonical organizer guards
# ============================================================

def require_current_organizer_member(
    membership=Depends(resolve_current_organizer_context),
):
    """
    Organizer member or above
    """
    if membership.role not in ACTIVE_ORGANIZER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organizer membership role is not supported",
        )
    return membership


def require_current_organizer_admin(
    membership=Depends(resolve_current_organizer_context),
):
    """
    Organizer admin / owner

    使用於：
    - canonical organizer APIs
    - approve submission
    """

    if membership.role not in ORGANIZER_MANAGEMENT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organizer admin access required",
        )

    return membership


def require_current_organizer_owner(
    membership=Depends(resolve_current_organizer_context),
):
    """Only the owner of the organizer can perform ownership-level actions."""
    if membership.role != ORGANIZER_OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organizer owner access required",
        )
    return membership


# ============================================================
# Compatibility identity helpers (legacy)
# ============================================================

def get_current_identity(
    user=Depends(get_current_user),
):
    """
    Legacy helper for APIs that expect identity dict

    ⚠️ 新 API 不應再使用
    """
    return user


# ============================================================
# Explicit aliases (IMPORTANT)
# ============================================================
# 為了避免 router 誤用 guard，明確命名
# ------------------------------------------------------------

# 🔹 Legacy（token-based，不吃 organizer_uuid）
require_organizer_admin_legacy = require_organizer_admin

# 🔹 Canonical（path-based，一定吃 organizer_uuid）
require_organizer_member = require_current_organizer_member
require_organizer_admin = require_current_organizer_admin
require_organizer_owner = require_current_organizer_owner

# Compatibility name used by dormant legacy admin modules.
get_current_super_admin = require_super_admin
