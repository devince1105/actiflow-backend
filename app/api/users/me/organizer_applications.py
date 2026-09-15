from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth.dependencies import get_current_user_obj
from app.core.db import get_db
from app.models.organizer.organizer_application import OrganizerApplication
from app.models.user.user import User
from app.schemas.organizer_application.organizer_application_create import (
    OrganizerApplicationCreate,
)


router = APIRouter(
    prefix="/users/me/organizer-applications",
    tags=["Users - Me - Organizer Applications"],
)


class MyOrganizerApplicationResponse(BaseModel):
    uuid: UUID
    name: str
    description: str | None = None
    application_reason: str | None = None
    contact_email: str
    phone: str | None = None
    website: str | None = None
    address: str | None = None
    status: str
    review_reason: str | None = None
    submitted_at: datetime
    reviewed_at: datetime | None = None


@router.get("", response_model=list[MyOrganizerApplicationResponse])
def list_my_organizer_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_obj),
):
    applications = (
        db.query(OrganizerApplication)
        .filter(
            OrganizerApplication.user_uuid == current_user.uuid,
            OrganizerApplication.is_deleted == False,
        )
        .order_by(OrganizerApplication.submitted_at.desc())
        .all()
    )
    return [_serialize(application, current_user.email) for application in applications]


@router.post(
    "",
    response_model=MyOrganizerApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_my_organizer_application(
    data: OrganizerApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_obj),
):
    if not current_user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="請先完成 Email 驗證",
        )

    pending = (
        db.query(OrganizerApplication.uuid)
        .filter(
            OrganizerApplication.user_uuid == current_user.uuid,
            OrganizerApplication.status == "pending",
            OrganizerApplication.is_deleted == False,
        )
        .first()
    )
    if pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="已有審核中的組織申請",
        )

    application_data = {
        "name": data.name.strip(),
        "description": data.description.strip(),
        "application_reason": data.reason.strip(),
        "email": str(data.contact_email or current_user.email).lower(),
        "phone": data.phone.strip() if data.phone else None,
        "website": str(data.website) if data.website else None,
        "address": (
            {"formatted": data.address.strip()} if data.address else None
        ),
    }
    application = OrganizerApplication(
        user_uuid=current_user.uuid,
        application_data=application_data,
        status="pending",
        created_by=current_user.uuid,
        created_by_role="applicant",
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return _serialize(application, current_user.email)


def _serialize(
    application: OrganizerApplication,
    fallback_email: str,
) -> MyOrganizerApplicationResponse:
    data = application.application_data or {}
    return MyOrganizerApplicationResponse(
        uuid=application.uuid,
        name=data.get("name") or data.get("organization_name") or "未提供名稱",
        description=data.get("description"),
        application_reason=data.get("application_reason"),
        contact_email=data.get("email") or fallback_email,
        phone=data.get("phone"),
        website=data.get("website"),
        address=(
            data.get("address", {}).get("formatted")
            if isinstance(data.get("address"), dict)
            else data.get("address")
        ),
        status=application.status,
        review_reason=application.reason,
        submitted_at=application.submitted_at,
        reviewed_at=application.reviewed_at,
    )
