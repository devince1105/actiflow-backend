# app/models/submission/submission_audit.py
from datetime import datetime, timezone
from uuid import UUID as PyUUID

from sqlalchemy import ForeignKey, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base.base_model import BaseModel

class SubmissionAuditLog(BaseModel, Base):
    """
    報名狀態變更稽核日誌 (Audit Log)
    """
    __tablename__ = "submission_audit_logs"

    submission_uuid: Mapped[PyUUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("submissions.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    actor_uuid: Mapped[PyUUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    actor_role: Mapped[str] = mapped_column(String, nullable=False) # system, organizer, user

    action_type: Mapped[str] = mapped_column(String, nullable=False) # approve, reject, cancel, reopen

    old_status: Mapped[str] = mapped_column(String, nullable=True)
    new_status: Mapped[str] = mapped_column(String, nullable=False)

    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_data: Mapped[dict] = mapped_column(JSONB, default=dict)
