# app/api/users/me/me.py

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.jwt import decode_access_token

from app.models.user.user import User
from app.models.organizer.organizer import Organizer
from app.models.membership.organizer_membership import OrganizerMembership
from app.models.membership.system_membership import SystemMembership
from app.models.auth.refresh_token import RefreshToken
from app.models.user.user_profile import UserProfile
from app.models.user.user_settings import UserSettings
from app.api.auth.dependencies import get_current_user_obj
from app.core.security import hash_password, verify_password
from app.schemas.user.account_settings import (
    AccountProfileResponse,
    AccountProfileUpdate,
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
    PasswordChangeRequest,
)

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
        "avatar_url": current_user.avatar_url,
        "role": "user",
        "memberships": memberships,
    }


# ============================================================
# PUT /users/me
# ============================================================
from app.schemas.user.user_update import UserUpdate
from app.crud.user.crud_user import user_crud

@router.put("")
def update_current_user(
    data: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    更新目前登入使用者的資訊（例如：頭像網址）
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

    # 執行更新
    updated_user = user_crud.update(
        db=db,
        db_obj=current_user,
        data=data
    )

    return {
        "status": "success",
        "message": "User updated successfully",
        "avatar_url": updated_user.avatar_url
    }


@router.get(
    "/account-settings",
    response_model=AccountProfileResponse,
)
def get_account_settings(
    current_user: User = Depends(get_current_user_obj),
):
    config = current_user.config or {}
    profile = current_user.profile
    return AccountProfileResponse(
        email=current_user.email,
        is_email_verified=current_user.is_email_verified,
        auth_provider=current_user.auth_provider,
        display_name=config.get("display_name"),
        phone=config.get("phone"),
        birthday=profile.birthday.date() if profile and profile.birthday else None,
        address=profile.address if profile else None,
        created_at=current_user.created_at,
    )


@router.put(
    "/account-settings/profile",
    response_model=AccountProfileResponse,
)
def update_account_profile(
    data: AccountProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_obj),
):
    updates = data.model_dump(exclude_unset=True)
    config = dict(current_user.config or {})
    for key in ("display_name", "phone"):
        if key in updates:
            value = updates.pop(key)
            config[key] = value.strip() if isinstance(value, str) else value
    current_user.config = config

    if updates:
        profile = current_user.profile
        if not profile:
            profile = UserProfile(user_uuid=current_user.uuid)
            db.add(profile)
        for key, value in updates.items():
            setattr(profile, key, value)

    db.commit()
    db.refresh(current_user)
    return get_account_settings(current_user)


@router.put("/account-settings/password")
def change_account_password(
    data: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_obj),
):
    if not current_user.password_hash or not verify_password(
        data.current_password,
        current_user.password_hash,
    ):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if verify_password(data.new_password, current_user.password_hash):
        raise HTTPException(
            status_code=400,
            detail="New password must be different",
        )

    current_user.password_hash = hash_password(data.new_password)
    (
        db.query(RefreshToken)
        .filter(
            RefreshToken.user_uuid == current_user.uuid,
            RefreshToken.revoked == False,
        )
        .update({"revoked": True}, synchronize_session=False)
    )
    db.commit()
    return {
        "message": "Password updated",
        "refresh_tokens_revoked": True,
    }


@router.get(
    "/account-settings/notifications",
    response_model=NotificationSettingsResponse,
)
def get_notification_settings(
    current_user: User = Depends(get_current_user_obj),
):
    settings = current_user.settings
    if not settings:
        return NotificationSettingsResponse()
    return NotificationSettingsResponse(
        notify_email=settings.notify_email,
        notify_sms=settings.notify_sms,
        notify_marketing=settings.notify_marketing,
    )


@router.put(
    "/account-settings/notifications",
    response_model=NotificationSettingsResponse,
)
def update_notification_settings(
    data: NotificationSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_obj),
):
    settings = current_user.settings
    if not settings:
        settings = UserSettings(user_uuid=current_user.uuid)
        db.add(settings)
    for key, value in data.model_dump().items():
        setattr(settings, key, value)
    db.commit()
    db.refresh(settings)
    return NotificationSettingsResponse.model_validate(
        settings,
        from_attributes=True,
    )
