# src/app/crud/submission/crud_submission.py
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session, selectinload

from app.crud.base.crud_base import CRUDBase
from app.models.submission.submission import Submission
from app.models.submission.submission_value import SubmissionValue
from app.schemas.submission.submission_create import SubmissionCreate
from app.schemas.submission.submission_update import (
    SubmissionUpdate,
    SubmissionStatusUpdate,
    SubmissionStatus,
)


class CRUDSubmission(CRUDBase[Submission]):
    """
    Submission CRUD (v1)
    -------------------------------------------------
    核心語意：
    - submitted_by_* : 報名動作執行者（登入使用者）
    - user_email     : 實際參加者 / 被報名者
    """

    # -------------------------------------------------
    # 建立 Submission
    # -------------------------------------------------
    def create(
        self,
        db: Session,
        data: SubmissionCreate,
        *,
        submitted_by_uuid: UUID | None = None,
        submitted_by_email: str | None = None,
        creator_role: str | None = None,
    ) -> Submission:
        obj_in = data.model_dump()

        if submitted_by_uuid:
            obj_in["submitted_by_uuid"] = submitted_by_uuid
            obj_in["submitted_by_email"] = submitted_by_email
            obj_in["created_by"] = submitted_by_uuid
            obj_in["created_by_role"] = creator_role

        return super().create(db, obj_in=obj_in)

    # -------------------------------------------------
    # 一般更新
    # -------------------------------------------------
    def update(
        self,
        db: Session,
        db_obj: Submission,
        data: SubmissionUpdate,
        *,
        updater_uuid: UUID | None = None,
        updater_role: str | None = None,
    ) -> Submission:
        obj_in = data.model_dump(exclude_unset=True)

        if updater_uuid:
            obj_in["updated_by"] = updater_uuid
            obj_in["updated_by_role"] = updater_role

        return super().update(db, db_obj=db_obj, obj_in=obj_in)

    # -------------------------------------------------
    # 更新狀態（流程 / 系統用）
    # -------------------------------------------------
    def update_status(
        self,
        db: Session,
        db_obj: Submission,
        data: SubmissionStatusUpdate,
        *,
        updater_uuid: UUID | None = None,
        updater_role: str | None = None,
    ) -> Submission:
        obj_in = {
            "status": data.status.value,
            "status_reason": data.status_reason,
        }

        if updater_uuid:
            obj_in["updated_by"] = updater_uuid
            obj_in["updated_by_role"] = updater_role

        return super().update(db, db_obj=db_obj, obj_in=obj_in)

    # -------------------------------------------------
    # 依 UUID 取得（共用）
    # -------------------------------------------------
    def get_by_uuid(
        self,
        db: Session,
        uuid: UUID,
    ) -> Optional[Submission]:
        return (
            db.query(self.model)
            .filter(
                self.model.uuid == uuid,
                self.model.is_deleted == False,
            )
            .first()
        )

    # -------------------------------------------------
    # Public tracking（依 submission_code）
    # -------------------------------------------------
    def get_by_code(
        self,
        db: Session,
        submission_code: str,
    ) -> Optional[Submission]:
        return (
            db.query(self.model)
            .filter(
                self.model.submission_code == submission_code,
                self.model.is_deleted == False,
            )
            .first()
        )

    # =================================================
    # ⭐ 我提交的 submissions（submitter 視角）
    # =================================================
    def list_by_submitter(
        self,
        db: Session,
        *,
        submitted_by_uuid: UUID,
    ) -> List[Submission]:
        """
        /users/me/submissions
        - 我「提交」的報名紀錄
        """
        return (
            db.query(self.model)
            .options(
                selectinload(self.model.event),
            )
            .filter(
                self.model.submitted_by_uuid == submitted_by_uuid,
                self.model.is_deleted == False,
                self.model.is_active == True,
            )
            .order_by(self.model.created_at.desc())
            .all()
        )

    # -------------------------------------------------
    # 單筆（submitter ownership）
    # -------------------------------------------------
    def get_by_uuid_and_submitter(
        self,
        db: Session,
        *,
        submission_uuid: UUID,
        submitted_by_uuid: UUID,
    ) -> Optional[Submission]:
        return (
            db.query(self.model)
            .options(
                selectinload(self.model.event),
                selectinload(self.model.values)
                    .selectinload(SubmissionValue.field),
                selectinload(self.model.values)
                    .selectinload(SubmissionValue.files),
            )
            .filter(
                self.model.uuid == submission_uuid,
                self.model.submitted_by_uuid == submitted_by_uuid,
                self.model.is_deleted == False,
                self.model.is_active == True,
            )
            .first()
        )

    # =================================================
    # ⚠️ Legacy / Transitional
    # =================================================
    def list_by_identity_fallback(
        self,
        db: Session,
        *,
        user_email: str,
    ) -> List[Submission]:
        """
        僅用於：
        - email 驗證
        - 舊資料補齊
        """
        return (
            db.query(self.model)
            .filter(
                self.model.user_email == user_email,
                self.model.is_deleted == False,
            )
            .order_by(self.model.created_at.desc())
            .all()
        )

    # -------------------------------------------------
    # Soft delete
    # -------------------------------------------------
    def soft_delete(
        self,
        db: Session,
        db_obj: Submission,
        *,
        deleter_uuid: UUID | None = None,
        deleter_role: str | None = None,
    ) -> Submission:
        obj_in = {
            "is_deleted": True,
            "status": SubmissionStatus.DELETED.value,
        }

        if deleter_uuid:
            obj_in["deleted_by"] = deleter_uuid
            obj_in["deleted_by_role"] = deleter_role

        return super().update(db, db_obj=db_obj, obj_in=obj_in)

    # =================================================
    # ⭐ 被報名者視角（participations）
    # =================================================
    def list_participations_by_user(
        self,
        db: Session,
        *,
        user_uuid: UUID,
    ) -> list[Submission]:
        """
        /users/me/participations
        - 僅限「實際參與者」
        - 必須已註冊為 User
        """
        return (
            db.query(self.model)
            .options(
                selectinload(self.model.event),
            )
            .filter(
                self.model.is_deleted == False,
                self.model.user_uuid == user_uuid,
            )
            .order_by(self.model.submitted_at.desc())
            .all()
        )


submission_crud = CRUDSubmission(Submission)
