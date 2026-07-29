from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.dependencies import require_super_admin
from app.models.event.event import Event
from app.models.membership.organizer_membership import OrganizerMembership
from app.models.organizer.organizer import Organizer
from app.models.organizer.organizer_application import OrganizerApplication
from app.models.system.system_audit_log import SystemAuditLog
from app.schemas.admin.organizers import (
    AdminOrganizerApplicationItem,
    AdminOrganizerApplicationListResponse,
    AdminOrganizerApplicationReview,
    AdminOrganizerListItem,
    AdminOrganizerListResponse,
)


router = APIRouter(
    prefix="/admin/organizers",
    tags=["Admin - Organizers"],
)


@router.get("", response_model=AdminOrganizerListResponse)
def list_admin_organizers(
    search: str = Query(default="", max_length=200),
    db: Session = Depends(get_db),
    _admin=Depends(require_super_admin),
):
    query = db.query(Organizer).filter(Organizer.is_deleted == False)
    normalized_search = search.strip()
    if normalized_search:
        query = query.filter(Organizer.name.ilike(f"%{normalized_search}%"))

    organizers = query.order_by(Organizer.created_at.desc()).all()
    organizer_uuids = [organizer.uuid for organizer in organizers]
    member_counts: dict = {}
    event_counts: dict = {}

    if organizer_uuids:
        member_counts = dict(
            db.query(
                OrganizerMembership.organizer_uuid,
                func.count(OrganizerMembership.id),
            )
            .filter(
                OrganizerMembership.organizer_uuid.in_(organizer_uuids),
                OrganizerMembership.is_deleted == False,
                OrganizerMembership.is_active == True,
            )
            .group_by(OrganizerMembership.organizer_uuid)
            .all()
        )
        event_counts = dict(
            db.query(Event.organizer_uuid, func.count(Event.id))
            .filter(
                Event.organizer_uuid.in_(organizer_uuids),
                Event.is_deleted == False,
            )
            .group_by(Event.organizer_uuid)
            .all()
        )

    return AdminOrganizerListResponse(
        items=[
            AdminOrganizerListItem(
                uuid=organizer.uuid,
                name=organizer.name,
                email=organizer.email,
                status=organizer.status,
                is_active=organizer.is_active,
                members_count=member_counts.get(organizer.uuid, 0),
                events_count=event_counts.get(organizer.uuid, 0),
                created_at=organizer.created_at,
            )
            for organizer in organizers
        ],
        total=len(organizers),
    )


@router.get(
    "/applications",
    response_model=AdminOrganizerApplicationListResponse,
)
def list_admin_organizer_applications(
    application_status: str = Query(
        default="pending",
        alias="status",
        pattern="^(pending|approved|rejected|all)$",
    ),
    db: Session = Depends(get_db),
    _admin=Depends(require_super_admin),
):
    query = db.query(OrganizerApplication).filter(
        OrganizerApplication.is_deleted == False
    )
    if application_status != "all":
        query = query.filter(
            OrganizerApplication.status == application_status
        )

    applications = query.order_by(
        OrganizerApplication.submitted_at.desc()
    ).all()
    return AdminOrganizerApplicationListResponse(
        items=[_serialize_application(application) for application in applications],
        total=len(applications),
    )


@router.post(
    "/applications/{application_uuid}/approve",
    response_model=AdminOrganizerApplicationItem,
)
def approve_admin_organizer_application(
    application_uuid: UUID,
    review: AdminOrganizerApplicationReview,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_super_admin),
):
    application = _get_pending_application(db, application_uuid)
    data = application.application_data or {}
    organization_name = data.get("name") or data.get("organization_name")
    if not organization_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Application is missing organization name",
        )

    organizer = Organizer(
        name=organization_name,
        email=data.get("email") or application.user.email,
        phone=data.get("phone"),
        website=data.get("website"),
        description=data.get("description"),
        logo_url=data.get("logo_url"),
        banner_url=data.get("banner_url"),
        address=data.get("address"),
        status="approved",
        is_active=True,
        created_by=application.user_uuid,
        created_by_role="applicant",
    )
    db.add(organizer)
    db.flush()
    db.add(
        OrganizerMembership(
            user_uuid=application.user_uuid,
            organizer_uuid=organizer.uuid,
            role="owner",
            is_active=True,
            is_suspended=False,
            created_by=UUID(admin["uuid"]),
            created_by_role="super_admin",
        )
    )

    _complete_review(application, admin, "approved", review.reason)
    _add_audit_log(
        db,
        request,
        admin,
        action="approve_organizer_application",
        target_uuid=application.uuid,
        before={"status": "pending"},
        after={"status": "approved", "organizer_uuid": str(organizer.uuid)},
        reason=review.reason,
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to create organizer from this application",
        ) from exc
    db.refresh(application)
    return _serialize_application(application)


@router.post(
    "/applications/{application_uuid}/reject",
    response_model=AdminOrganizerApplicationItem,
)
def reject_admin_organizer_application(
    application_uuid: UUID,
    review: AdminOrganizerApplicationReview,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_super_admin),
):
    application = _get_pending_application(db, application_uuid)
    _complete_review(application, admin, "rejected", review.reason)
    _add_audit_log(
        db,
        request,
        admin,
        action="reject_organizer_application",
        target_uuid=application.uuid,
        before={"status": "pending"},
        after={"status": "rejected"},
        reason=review.reason,
    )
    db.commit()
    db.refresh(application)
    return _serialize_application(application)


def _get_pending_application(
    db: Session,
    application_uuid: UUID,
) -> OrganizerApplication:
    application = (
        db.query(OrganizerApplication)
        .filter(
            OrganizerApplication.uuid == application_uuid,
            OrganizerApplication.is_deleted == False,
        )
        .first()
    )
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    if application.status != "pending":
        raise HTTPException(
            status_code=409,
            detail="Application has already been reviewed",
        )
    return application


def _complete_review(
    application: OrganizerApplication,
    admin: dict,
    review_status: str,
    reason: str | None,
) -> None:
    application.status = review_status
    application.reason = reason
    application.reviewed_at = datetime.now(timezone.utc)
    application.reviewer_uuid = UUID(admin["uuid"])
    application.reviewer_role = "super_admin"


def _add_audit_log(
    db: Session,
    request: Request,
    admin: dict,
    *,
    action: str,
    target_uuid: UUID,
    before: dict,
    after: dict,
    reason: str | None,
) -> None:
    db.add(
        SystemAuditLog(
            audit_code=f"AUD-{uuid4().hex.upper()}",
            user_uuid=UUID(admin["uuid"]),
            user_email=admin["email"],
            user_role="super_admin",
            action=action,
            target_type="OrganizerApplication",
            target_uuid=target_uuid,
            before_data=before,
            after_data=after,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            extra={"reason": reason} if reason else {},
        )
    )


def _serialize_application(
    application: OrganizerApplication,
) -> AdminOrganizerApplicationItem:
    data = application.application_data or {}
    return AdminOrganizerApplicationItem(
        uuid=application.uuid,
        user_uuid=application.user_uuid,
        applicant_email=application.user.email,
        organization_name=(
            data.get("name")
            or data.get("organization_name")
            or "未提供名稱"
        ),
        application_data=data,
        reason=application.reason,
        status=application.status,
        submitted_at=application.submitted_at,
        reviewed_at=application.reviewed_at,
    )
