# app/api/users/me/me.py

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.jwt import decode_access_token

from app.models.user.user import User
from app.models.organizer.organizer import Organizer
from app.models.membership.organizer_membership import OrganizerMembership
from app.models.membership.system_membership import SystemMembership

router = APIRouter(
    prefix="/users/me",
    tags=["Users - Me"],
)


# ============================================================
# GET /users/me
# ============================================================
@router.get("")
def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    取得目前登入使用者的 Auth Context（User 視角）
    """

    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_access_token(access_token)
    user_uuid = payload.get("sub")
    if not user_uuid:
        raise HTTPException(status_code=401, detail="Invalid token")

    current_user = (
        db.query(User)
        .filter(
            User.uuid == user_uuid,
            User.is_deleted == False,
        )
        .first()
    )

    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")

    # -----------------------------
    # System memberships
    # -----------------------------
    system_memberships = (
        db.query(SystemMembership)
        .filter(
            SystemMembership.user_uuid == current_user.uuid,
            SystemMembership.is_deleted == False,
            SystemMembership.is_active == True,
            SystemMembership.is_suspended == False,
        )
        .all()
    )

    # -----------------------------
    # Organizer memberships
    # -----------------------------
    organizer_memberships = (
        db.query(OrganizerMembership)
        .join(
            Organizer,
            Organizer.uuid == OrganizerMembership.organizer_uuid,
        )
        .filter(
            OrganizerMembership.user_uuid == current_user.uuid,
            OrganizerMembership.is_deleted == False,
            Organizer.is_deleted == False,
        )
        .all()
    )

    memberships: list[dict] = []

    for m in system_memberships:
        memberships.append({
            "type": "system",
            "role": m.role,
            "status": (
                "suspended"
                if m.is_suspended
                else "active" if m.is_active else "inactive"
            ),
        })

    for m in organizer_memberships:
        memberships.append({
            "type": "organizer",
            "organizer_uuid": str(m.organizer_uuid),
            "organizer_name": m.organizer.name,
            "membership_role": m.role,
        })

    return {
        "uuid": str(current_user.uuid),
        "email": current_user.email,
        "role": "user",
        "memberships": memberships,
    }
