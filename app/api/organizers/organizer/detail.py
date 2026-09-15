from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.dependencies import require_current_organizer_member
from app.models.organizer.organizer import Organizer
from app.schemas.organizer.public.organizer_public import OrganizerPublic


router = APIRouter(tags=["Organizer - Detail"])


@router.get("", response_model=OrganizerPublic)
def get_current_organizer(
    organizer_uuid: UUID,
    db: Session = Depends(get_db),
    _membership=Depends(require_current_organizer_member),
):
    """Return the current path-scoped organizer's non-sensitive profile."""
    organizer = (
        db.query(Organizer)
        .filter(
            Organizer.uuid == organizer_uuid,
            Organizer.is_deleted == False,
        )
        .first()
    )
    if not organizer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organizer not found",
        )
    return organizer
