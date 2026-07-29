# app/services/submission/submission_service.py

from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import update, select
from sqlalchemy.exc import IntegrityError
from fastapi import BackgroundTasks
import logging

from app.core.exceptions import ActiFlowBusinessException, ActiFlowErrorCode
from app.models.event.event import Event
from app.models.submission.submission import Submission
from app.models.submission.submission_value import SubmissionValue
from app.models.auth.email_verification import EmailVerification
from app.models.event.event_field import EventField

from app.api.utils.submission_code import generate_submission_code
from app.api.utils.email_sender import send_via_resend
from app.api.utils.email_templates import verification_email_html
from app.core.config import settings

# Setup logger for observability
logger = logging.getLogger("actiflow.submission")

class SubmissionService:
    CAPACITY_STATUSES = {"pending", "email_verified", "paid", "completed"}

    @staticmethod
    def can_register(event: Event, user_email: str = None) -> bool:
        if event.status != "published": return False
        if event.current_attendance >= event.max_capacity: return False
        if event.registration_deadline and datetime.now(timezone.utc) > event.registration_deadline: return False
        return True

    @staticmethod
    def register_event(
        db: Session,
        event_uuid: UUID,
        user_email: str,
        values: list,
        submitted_by_uuid: UUID = None,
        submitted_by_email: str = None,
        background_tasks: BackgroundTasks = None,
        ip_address: str = None,
        user_agent: str = None,
        notes: str = None,
        extra_data: dict = None,
    ) -> Submission:
        event = db.query(Event).filter(Event.uuid == event_uuid).first()
        if not event:
            raise ActiFlowBusinessException(code=ActiFlowErrorCode.EVENT_NOT_FOUND, message="Event not found", status_code=404)

        if not SubmissionService.can_register(event, user_email):
            raise ActiFlowBusinessException(code=ActiFlowErrorCode.EVENT_FULL, message="Event is full or closed")

        try:
            # Create Submission
            submission = Submission(
                submission_code=generate_submission_code(event.event_code),
                event_uuid=event_uuid,
                user_email=user_email,
                submitted_by_uuid=submitted_by_uuid,
                status="pending",
                notes=notes,
                extra_data=extra_data or {},
                ip_address=ip_address,
                user_agent=user_agent
            )
            db.add(submission)

            # Atomic Capacity
            stmt = update(Event).where(Event.uuid == event_uuid).where(Event.status == "published").where(Event.current_attendance < Event.max_capacity).values(current_attendance=Event.current_attendance + 1)
            result = db.execute(stmt)
            if result.rowcount == 0:
                  raise ActiFlowBusinessException(code=ActiFlowErrorCode.EVENT_FULL, message="Event became full")

            # Field Values
            event_fields = db.query(EventField).filter(EventField.event_uuid == event_uuid, EventField.is_deleted == False).all()
            field_map = {f.field_key: f for f in event_fields}
            sub_values = [SubmissionValue(submission_uuid=submission.uuid, event_field_uuid=field_map[v.field_key].uuid, field_key=v.field_key, value=v.value) for v in values if v.field_key in field_map]
            db.add_all(sub_values)

            # Verification
            token = uuid4().hex
            verification = EmailVerification(ref_type="submission", ref_uuid=submission.uuid, email=user_email, token=token, expires_at=datetime.now(timezone.utc) + timedelta(minutes=30))
            db.add(verification)

            db.commit()
            db.refresh(submission)

            if background_tasks:
                background_tasks.add_task(SubmissionService.send_verification_email, user_email, token)

            return submission
        except Exception as e:
            db.rollback()
            if isinstance(e, IntegrityError):
                raise ActiFlowBusinessException(
                    code=ActiFlowErrorCode.ALREADY_REGISTERED,
                    message="This email is already registered for the event",
                    status_code=409,
                ) from e
            raise

    @staticmethod
    def _check_permission(actor_role: str, target_status: str):
        PERMISSIONS = {
            "email_verified": ["system"],
            "paid": ["admin"],
            "confirmed": ["organizer", "admin"],
            "rejected": ["organizer", "admin"],
            "canceled": ["user", "admin", "organizer"],
            "pending": ["organizer", "admin"] # for reopen
        }
        allowed_roles = PERMISSIONS.get(target_status, [])
        if actor_role not in allowed_roles:
            raise ActiFlowBusinessException(code=ActiFlowErrorCode.UNAUTHORIZED, message=f"Role '{actor_role}' not allowed for status '{target_status}'")

    @staticmethod
    def _adjust_capacity_for_transition(
        db: Session,
        event_uuid: UUID,
        old_status: str,
        target_status: str,
    ) -> None:
        occupied_before = old_status in SubmissionService.CAPACITY_STATUSES
        occupied_after = target_status in SubmissionService.CAPACITY_STATUSES
        if occupied_before == occupied_after:
            return

        if occupied_after:
            result = db.execute(
                update(Event)
                .where(
                    Event.uuid == event_uuid,
                    Event.status == "published",
                    Event.current_attendance < Event.max_capacity,
                )
                .values(current_attendance=Event.current_attendance + 1)
            )
            if result.rowcount == 0:
                raise ActiFlowBusinessException(
                    code=ActiFlowErrorCode.EVENT_FULL,
                    message="Event became full",
                    status_code=409,
                )
            return

        db.execute(
            update(Event)
            .where(
                Event.uuid == event_uuid,
                Event.current_attendance > 0,
            )
            .values(current_attendance=Event.current_attendance - 1)
        )

    @staticmethod
    def update_status(db: Session, submission_uuid: UUID, target_status: str, actor_id: UUID = None, actor_role: str = "", reason: str = None) -> Submission:
        submission = db.query(Submission).filter(Submission.uuid == submission_uuid).first()
        if not submission: raise ActiFlowBusinessException(code=ActiFlowErrorCode.EVENT_NOT_FOUND, message="Not found", status_code=404)

        SubmissionService._check_permission(actor_role, target_status)

        old_status = submission.status.value if hasattr(submission.status, "value") else submission.status
        if old_status == target_status: return submission

        from app.crud.submission.crud_submission_status import assert_status_transition
        try:
            assert_status_transition(current=old_status, target=target_status)
        except Exception as exc:
            raise ActiFlowBusinessException(
                code=ActiFlowErrorCode.INVALID_STATUS_TRANSITION,
                message=str(exc),
                status_code=409,
            ) from exc

        SubmissionService._adjust_capacity_for_transition(
            db, submission.event_uuid, old_status, target_status
        )
        submission.status = target_status
        if reason: submission.status_reason = reason
        submission.updated_at = datetime.now(timezone.utc)

        from app.models.submission.submission_audit import SubmissionAuditLog
        audit = SubmissionAuditLog(submission_uuid=submission_uuid, actor_uuid=actor_id, actor_role=actor_role, action_type=target_status, old_status=old_status, new_status=target_status, reason=reason)
        db.add(audit)

        db.commit()
        db.refresh(submission)
        return submission

    @staticmethod
    def bulk_action(db: Session, event_uuid: UUID, submission_uuids: list[UUID], action: str, actor_id: UUID, actor_role: str, reason: str = None) -> dict:
        ACTION_MAP = {"approve": "confirmed", "reject": "rejected", "reopen": "pending", "cancel": "canceled"}
        target_status = ACTION_MAP.get(action)
        if not target_status: raise ActiFlowBusinessException(code=ActiFlowErrorCode.INVALID_STATUS, message="Invalid action")

        SubmissionService._check_permission(actor_role, target_status)

        submissions = db.query(Submission).filter(Submission.uuid.in_(submission_uuids), Submission.event_uuid == event_uuid).all()
        success_ids, fail_ids, errors = [], [], []

        from app.crud.submission.crud_submission_status import assert_status_transition
        from app.models.submission.submission_audit import SubmissionAuditLog

        for s in submissions:
            try:
                old_status = s.status.value if hasattr(s.status, "value") else s.status
                if old_status == target_status:
                    success_ids.append(str(s.uuid))
                    continue

                assert_status_transition(current=old_status, target=target_status)
                SubmissionService._adjust_capacity_for_transition(
                    db, s.event_uuid, old_status, target_status
                )
                s.status = target_status
                if reason: s.status_reason = reason

                audit = SubmissionAuditLog(submission_uuid=s.uuid, actor_uuid=actor_id, actor_role=actor_role, action_type=action, old_status=old_status, new_status=target_status, reason=reason)
                db.add(audit)
                success_ids.append(str(s.uuid))
            except Exception as e:
                fail_ids.append(str(s.uuid))
                errors.append(str(e))

        db.commit()
        return {"success_count": len(success_ids), "fail_count": len(fail_ids), "success_ids": success_ids, "errors": errors}

    @staticmethod
    def send_verification_email(email: str, token: str):
        try:
            verify_url = f"{settings.FRONTEND_BASE_URL}/verify-email?token={token}"
            html = verification_email_html(verify_url)
            send_via_resend(to_email=email, subject="請驗證您的活動報名", html=html)
        except Exception as e:
            logger.error(f"Failed email: {e}")
