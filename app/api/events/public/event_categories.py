# app/api/events/public/event_categories.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.event.event_category import EventCategory
from app.schemas.event.category.event_category_public import EventCategoryPublic

router = APIRouter(
    prefix="/public/event-categories",
    tags=["Public - Event Categories"],
)


# ============================================================
# Public: Event Category List (for Tabs / Filter)
# ============================================================
@router.get("", response_model=list[EventCategoryPublic])
def list_public_event_categories(
    db: Session = Depends(get_db),
):
    """
    公開活動分類清單（不需登入）

    用途：
    - 活動列表 Tabs
    - 首頁分類導覽
    - 前端 filter / routing
    """

    categories = (
        db.query(EventCategory)
        .filter(
            EventCategory.is_active == True,
            EventCategory.is_deleted == False,
        )
        .order_by(EventCategory.sort_order.asc())
        .all()
    )

    return categories
