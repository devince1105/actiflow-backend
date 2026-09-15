# app/crud/event/crud_event_field.py

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from uuid import UUID

from app.crud.base.crud_base import CRUDBase
from app.models.event.event_field import EventField
from app.schemas.event.field.event_field_create import EventFieldCreate
from app.schemas.event.field.event_field_update import EventFieldUpdate


class CRUDEventField(CRUDBase[EventField]):

    # ---------------------------------------------------------
    # List fields by event
    # ---------------------------------------------------------
    def list_by_event(
        self,
        db: Session,
        event_uuid: UUID,
    ) -> list[EventField]:
        return (
            db.query(EventField)
            .filter(
                EventField.event_uuid == event_uuid,
                EventField.is_deleted == False,
            )
            .order_by(EventField.sort_order.asc())
            .all()
        )

    # ---------------------------------------------------------
    # Create field  ⭐⭐⭐（重點修正）
    # ---------------------------------------------------------
    def create(
        self,
        db: Session,
        *,
        event_uuid: UUID,
        data: EventFieldCreate,
        created_by,
        created_by_role,
    ) -> EventField:
        # 1️⃣ 先檢查是否已存在（商業規則）
        existing = (
            db.query(EventField)
            .filter(
                EventField.event_uuid == event_uuid,
                EventField.field_key == data.field_key,
                EventField.is_deleted == False,
            )
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"欄位 key「{data.field_key}」已存在"
            )

        # 2️⃣ 建立物件
        obj = data.model_dump()
        obj.update(
            {
                "event_uuid": event_uuid,
                "created_by": created_by,
                "created_by_role": created_by_role,
            }
        )

        db_obj = EventField(**obj)
        db.add(db_obj)

        # 3️⃣ commit + 捕捉 race condition
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"欄位 key「{data.field_key}」已存在"
            )

        db.refresh(db_obj)
        return db_obj

    # ---------------------------------------------------------
    # Update field
    # ---------------------------------------------------------
    def update(
        self,
        db: Session,
        db_obj: EventField,
        data: EventFieldUpdate,
    ) -> EventField:
        return super().update(
            db,
            db_obj=db_obj,
            obj_in=data.model_dump(exclude_unset=True),
        )


# ---------------------------------------------------------
# CRUD instance
# ---------------------------------------------------------
event_field_crud = CRUDEventField(EventField)
