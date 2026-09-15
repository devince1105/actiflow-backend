from math import ceil

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.dependencies import require_super_admin
from app.models.membership.organizer_membership import OrganizerMembership
from app.models.membership.system_membership import SystemMembership
from app.models.submission.submission import Submission
from app.models.user.user import User
from app.schemas.admin.users import AdminUserListItem, AdminUserListResponse


router = APIRouter(
    prefix="/admin/users",
    tags=["Admin - Users"],
)


@router.get("", response_model=AdminUserListResponse)
def list_admin_users(
    search: str = Query(default="", max_length=254),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin=Depends(require_super_admin),
):
    query = db.query(User).filter(User.is_deleted == False)
    normalized_search = search.strip()
    if normalized_search:
        query = query.filter(User.email.ilike(f"%{normalized_search}%"))

    total = query.count()
    users = (
        query.order_by(User.created_at.desc(), User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    user_uuids = [user.uuid for user in users]

    system_roles: dict = {}
    organizer_counts: dict = {}
    submission_counts: dict = {}

    if user_uuids:
        role_rows = (
            db.query(SystemMembership.user_uuid, SystemMembership.role)
            .filter(
                SystemMembership.user_uuid.in_(user_uuids),
                SystemMembership.is_deleted == False,
                SystemMembership.is_active == True,
                SystemMembership.is_suspended == False,
            )
            .all()
        )
        for user_uuid, role in role_rows:
            system_roles.setdefault(user_uuid, []).append(role)

        organizer_counts = dict(
            db.query(
                OrganizerMembership.user_uuid,
                func.count(OrganizerMembership.id),
            )
            .filter(
                OrganizerMembership.user_uuid.in_(user_uuids),
                OrganizerMembership.is_deleted == False,
                OrganizerMembership.is_active == True,
            )
            .group_by(OrganizerMembership.user_uuid)
            .all()
        )
        submission_counts = dict(
            db.query(Submission.user_uuid, func.count(Submission.id))
            .filter(
                Submission.user_uuid.in_(user_uuids),
                Submission.is_deleted == False,
            )
            .group_by(Submission.user_uuid)
            .all()
        )

    return AdminUserListResponse(
        items=[
            AdminUserListItem(
                uuid=user.uuid,
                email=user.email,
                avatar_url=user.avatar_url,
                is_active=user.is_active,
                is_email_verified=user.is_email_verified,
                system_roles=system_roles.get(user.uuid, []),
                organizer_memberships_count=organizer_counts.get(user.uuid, 0),
                submissions_count=submission_counts.get(user.uuid, 0),
                created_at=user.created_at,
            )
            for user in users
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
    )
