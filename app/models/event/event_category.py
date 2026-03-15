# app/models/event/event_category.py

from typing import List, TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base.base_model import BaseModel

if TYPE_CHECKING:
    from app.models.event.event import Event


class EventCategory(BaseModel, Base):
    """
    活動分類主檔
    - 系統層級資料（不屬於 organizer）
    - 用於活動篩選 / UI 顯示
    """

    __tablename__ = "event_categories"

    # 業務識別（不可變）
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="分類代碼（例如 SPORTS_OUTDOOR）",
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="URL slug（sports-outdoor）",
    )

    label_zh: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    label_en: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    display_label_zh: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="前台顯示用短中文名稱（Tab / Pills）",
    )

    display_label_en: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="前台顯示用短英文名稱（Tab / Pills）",
    )

    icon: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="前台顯示用 icon（Tab / Pills）",
    )

    color: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="UI 顏色 token（對應前端 UIColor）",
    )

    sort_order: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        index=True,
    )

    # ---------------------------------------------------------
    # Relationships
    # ---------------------------------------------------------
    events: Mapped[List["Event"]] = relationship(
        "Event",
        back_populates="event_category",
        lazy="selectin",
    )