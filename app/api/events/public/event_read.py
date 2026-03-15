# app/api/events/public/event_read.py

from fastapi import APIRouter, Request, Depends
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.db import get_db
from app.core.jwt import decode_access_token
from app.models.event.event_view import EventView

router = APIRouter(prefix="/public/events")


@router.post("/{event_uuid}/view", status_code=204)
def record_event_view(
    event_uuid: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    # 預設為匿名
    user_uuid = None

    # 嘗試從 cookie 解析 user（不丟錯）
    access_token = request.cookies.get("access_token")
    if access_token:
        try:
            payload = decode_access_token(access_token)
            user_uuid = payload.get("sub")
        except Exception:
            # token 無效 → 視為匿名
            user_uuid = None

    ip_address = request.client.host if request.client else None

    view = EventView(
        event_id=event_uuid,
        user_id=user_uuid,
        ip_address=ip_address,
    )

    db.add(view)
    db.commit()


@router.get("/{event_uuid}/metrics")
def get_event_metrics(
    event_uuid: UUID,
    db: Session = Depends(get_db),
):
    view_count = (
        db.query(func.count(EventView.id))
        .filter(EventView.event_id == event_uuid)
        .scalar()
    )

    return {
        "event_uuid": event_uuid,
        "view_count": view_count,
    }