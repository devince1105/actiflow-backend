# app/core/dependencies.py

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from starlette import status

from app.core.db import get_db
from app.api.auth.dependencies import get_current_user
from app.models.membership.organizer_membership import OrganizerMembership

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

    if not any(m["role"] == "super_admin" for m in system_roles):
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
    identity=Depends(get_current_user),
):
    """
    Resolve organizer membership from DB (canonical)

    設計原則：
    - 不信任 token 內的 organizer 資訊
    - 以 path organizer_uuid + DB membership 為準
    """

    user_uuid = identity["uuid"]

    membership = (
        db.query(OrganizerMembership)
        .filter(
            OrganizerMembership.user_uuid == user_uuid,
            OrganizerMembership.organizer_uuid == organizer_uuid,
            OrganizerMembership.is_active == True,
            OrganizerMembership.is_deleted == False,
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

    if membership.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organizer admin access required",
        )

    return membership


# ============================================================
# Compatibility identity helpers (legacy)
# ============================================================

from app.api.auth.identity import build_identity

def get_current_identity(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Legacy helper for APIs that expect identity dict

    ⚠️ 新 API 不應再使用
    """
    return build_identity(db, user)


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
