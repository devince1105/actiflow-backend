from math import ceil

from fastapi import APIRouter, Depends, Query
from sqlalchemy import String, cast, func, or_
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.dependencies import require_super_admin
from app.models.system.system_audit_log import SystemAuditLog
from app.schemas.admin.audit_logs import (
    AdminAuditLogListItem,
    AdminAuditLogListResponse,
)


router = APIRouter(
    prefix="/admin/audit-logs",
    tags=["Admin - Audit Logs"],
)


@router.get("", response_model=AdminAuditLogListResponse)
def list_admin_audit_logs(
    search: str = Query(default="", max_length=254),
    action: str = Query(default="", max_length=100),
    target_type: str = Query(default="", max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin=Depends(require_super_admin),
):
    base_filter = SystemAuditLog.is_deleted == False
    query = db.query(SystemAuditLog).filter(base_filter)
    normalized_search = search.strip()
    if normalized_search:
        pattern = f"%{normalized_search}%"
        query = query.filter(
            or_(
                SystemAuditLog.audit_code.ilike(pattern),
                SystemAuditLog.user_email.ilike(pattern),
                SystemAuditLog.action.ilike(pattern),
                SystemAuditLog.target_type.ilike(pattern),
                cast(SystemAuditLog.target_uuid, String).ilike(pattern),
            )
        )
    if action:
        query = query.filter(SystemAuditLog.action == action)
    if target_type:
        query = query.filter(SystemAuditLog.target_type == target_type)

    total = query.count()
    logs = (
        query.order_by(
            SystemAuditLog.timestamp.desc(),
            SystemAuditLog.id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    action_counts = dict(
        db.query(SystemAuditLog.action, func.count(SystemAuditLog.id))
        .filter(base_filter)
        .group_by(SystemAuditLog.action)
        .all()
    )
    target_types = [
        row[0]
        for row in (
            db.query(SystemAuditLog.target_type)
            .filter(
                base_filter,
                SystemAuditLog.target_type.is_not(None),
            )
            .distinct()
            .order_by(SystemAuditLog.target_type)
            .all()
        )
    ]

    return AdminAuditLogListResponse(
        items=[
            AdminAuditLogListItem(
                uuid=log.uuid,
                audit_code=log.audit_code,
                user_uuid=log.user_uuid,
                user_email=log.user_email,
                user_role=log.user_role,
                action=log.action,
                target_type=log.target_type,
                target_uuid=log.target_uuid,
                before_data=log.before_data,
                after_data=log.after_data,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                extra=log.extra or {},
                timestamp=log.timestamp,
            )
            for log in logs
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
        action_counts=action_counts,
        target_types=target_types,
    )
