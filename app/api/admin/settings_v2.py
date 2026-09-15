from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.dependencies import require_super_admin
from app.models.system.system_audit_log import SystemAuditLog
from app.models.system.system_settings import SystemSettings
from app.schemas.admin.settings import (
    AdminSystemSettingsResponse,
    AdminSystemSettingsUpdate,
)


router = APIRouter(
    prefix="/admin/settings",
    tags=["Admin - Settings"],
)

SAFE_CONFIG_DEFAULTS = {
    "maintenance_mode": False,
    "registration_enabled": True,
    "organizer_applications_enabled": True,
    "default_event_capacity": 100,
    "max_image_size_mb": 5,
}


@router.get("", response_model=AdminSystemSettingsResponse)
def get_admin_system_settings(
    db: Session = Depends(get_db),
    _admin=Depends(require_super_admin),
):
    settings = _get_settings(db)
    return _serialize_settings(settings)


@router.put("", response_model=AdminSystemSettingsResponse)
def update_admin_system_settings(
    data: AdminSystemSettingsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_super_admin),
):
    settings = _get_settings(db)
    current_version = settings.version if settings else 0
    if data.expected_version != current_version:
        raise HTTPException(
            status_code=409,
            detail="Settings changed since this page was loaded",
        )

    before = _serialize_settings(settings).model_dump(mode="json")
    if not settings:
        settings = SystemSettings(
            site_name="ActiFlow",
            config={},
            is_active=True,
            version=0,
        )
        db.add(settings)
        db.flush()

    updates = data.model_dump(
        exclude={"expected_version"},
        exclude_unset=True,
    )
    config = dict(settings.config or {})
    for key in SAFE_CONFIG_DEFAULTS:
        if key in updates:
            config[key] = updates.pop(key)

    for field in ("site_name", "logo_url", "support_email"):
        if field in updates:
            value = updates[field]
            setattr(settings, field, str(value) if value is not None else None)

    settings.config = config
    settings.version = current_version + 1
    settings.updated_by = UUID(admin["uuid"])
    settings.updated_by_role = "super_admin"
    after = _serialize_settings(settings).model_dump(mode="json")

    db.add(
        SystemAuditLog(
            audit_code=f"AUD-{uuid4().hex.upper()}",
            user_uuid=UUID(admin["uuid"]),
            user_email=admin["email"],
            user_role="super_admin",
            action="update_system_settings",
            target_type="SystemSettings",
            target_uuid=settings.uuid,
            before_data=before,
            after_data=after,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            extra={},
        )
    )
    db.commit()
    db.refresh(settings)
    return _serialize_settings(settings)


def _get_settings(db: Session) -> SystemSettings | None:
    return (
        db.query(SystemSettings)
        .filter(SystemSettings.is_deleted == False)
        .order_by(SystemSettings.id.asc())
        .first()
    )


def _serialize_settings(
    settings: SystemSettings | None,
) -> AdminSystemSettingsResponse:
    if not settings:
        return AdminSystemSettingsResponse()

    config = settings.config or {}
    safe_config = {
        key: config.get(key, default)
        for key, default in SAFE_CONFIG_DEFAULTS.items()
    }
    return AdminSystemSettingsResponse(
        uuid=settings.uuid,
        site_name=settings.site_name,
        logo_url=settings.logo_url,
        support_email=settings.support_email,
        version=settings.version,
        **safe_config,
    )
