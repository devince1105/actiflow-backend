# app/services/submission/submission_service.py

from datetime import date, datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import func, update, select
from sqlalchemy.exc import IntegrityError
from fastapi import BackgroundTasks
import logging
from typing import NoReturn
from email_validator import EmailNotValidError, validate_email

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
from app.services.submission.notification import (
    send_submission_status_email,
)

# Setup logger for observability
logger = logging.getLogger("actiflow.submission")

class SubmissionService:
    CAPACITY_STATUSES = {"pending", "email_verified", "paid", "completed"}
    SUPPORTED_FIELD_TYPES = {
        "text",
        "textarea",
        "email",
        "tel",
        "number",
        "select",
        "radio",
        "checkbox",
        "date",
    }
    MAX_TEXT_LENGTH = 10_000
    MAX_CHECKBOX_VALUES = 100

    @staticmethod
    def can_register(event: Event, user_email: str = None) -> bool:
        if not getattr(event, "is_active", True): return False
        if getattr(event, "is_deleted", False): return False
        if event.status != "published": return False
        if event.current_attendance >= event.max_capacity: return False
        if event.registration_deadline:
            deadline = event.registration_deadline
            now = (
                datetime.now(timezone.utc)
                if deadline.tzinfo is not None
                else datetime.now()
            )
            if now > deadline:
                return False
        return True

    @staticmethod
    def _validated_field_map(
        db: Session,
        event_uuid: UUID,
        values: list,
    ) -> dict[str, EventField]:
        event_fields = (
            db.query(EventField)
            .filter(
                EventField.event_uuid == event_uuid,
                EventField.is_active == True,
                EventField.is_enabled == True,
                EventField.is_deleted == False,
            )
            .all()
        )
        field_map = {field.field_key: field for field in event_fields}

        submitted: dict[str, object] = {}
        for item in values:
            if item.field_key in submitted:
                raise ActiFlowBusinessException(
                    code=ActiFlowErrorCode.INVALID_SUBMISSION_DATA,
                    message=f"Duplicate field: {item.field_key}",
                    status_code=422,
                )
            submitted[item.field_key] = item.value

        missing = sorted(
            field.field_key
            for field in event_fields
            if field.required
            and (
                field.field_key not in submitted
                or submitted[field.field_key] is None
                or submitted[field.field_key] == ""
                or submitted[field.field_key] == []
                or (
                    field.field_type == "checkbox"
                    and submitted[field.field_key] is False
                )
            )
        )
        if missing:
            raise ActiFlowBusinessException(
                code=ActiFlowErrorCode.INVALID_SUBMISSION_DATA,
                message="Required registration fields are missing",
                status_code=422,
                detail={"missing_fields": missing},
            )

        unknown = sorted(set(submitted) - set(field_map))
        if unknown:
            raise ActiFlowBusinessException(
                code=ActiFlowErrorCode.INVALID_SUBMISSION_DATA,
                message="Unknown or disabled registration fields",
                status_code=422,
                detail={"unknown_fields": unknown},
            )

        for field_key, value in submitted.items():
            SubmissionService._validate_field_value(field_map[field_key], value)

        return field_map

    @staticmethod
    def _invalid_field(field: EventField, reason: str) -> NoReturn:
        raise ActiFlowBusinessException(
            code=ActiFlowErrorCode.INVALID_SUBMISSION_DATA,
            message=f"Invalid value for field: {field.field_key}",
            status_code=422,
            detail={"field_key": field.field_key, "reason": reason},
        )

    @staticmethod
    def _option_values(field: EventField) -> set[str]:
        if not isinstance(field.options, list):
            return set()

        values: set[str] = set()
        for option in field.options:
            if isinstance(option, str):
                values.add(option)
            elif isinstance(option, dict):
                value = option.get("value", option.get("label"))
                if isinstance(value, (str, int, float)) and not isinstance(
                    value, bool
                ):
                    values.add(str(value))
        return values

    @staticmethod
    def _validate_field_value(field: EventField, value: object) -> None:
        field_type = field.field_type
        if field_type not in SubmissionService.SUPPORTED_FIELD_TYPES:
            SubmissionService._invalid_field(field, "unsupported_field_type")

        if value is None or value == "" or value == []:
            if field.required:
                SubmissionService._invalid_field(field, "required")
            return

        validation = field.validation if isinstance(field.validation, dict) else {}

        if field_type in {"text", "textarea", "email", "tel", "date"}:
            if not isinstance(value, str):
                SubmissionService._invalid_field(field, "must_be_string")

            min_length = validation.get("min_length", 0)
            max_length = validation.get(
                "max_length",
                SubmissionService.MAX_TEXT_LENGTH,
            )
            if not isinstance(min_length, int) or min_length < 0:
                min_length = 0
            if not isinstance(max_length, int) or max_length < 0:
                max_length = SubmissionService.MAX_TEXT_LENGTH
            max_length = min(max_length, SubmissionService.MAX_TEXT_LENGTH)

            if len(value) < min_length:
                SubmissionService._invalid_field(field, "too_short")
            if len(value) > max_length:
                SubmissionService._invalid_field(field, "too_long")

            if field_type == "email":
                try:
                    validate_email(value, check_deliverability=False)
                except EmailNotValidError:
                    SubmissionService._invalid_field(field, "invalid_email")
            elif field_type == "date":
                try:
                    date.fromisoformat(value)
                except ValueError:
                    SubmissionService._invalid_field(field, "invalid_date")
            return

        if field_type == "number":
            if isinstance(value, bool) or not isinstance(value, (str, int, float)):
                SubmissionService._invalid_field(field, "must_be_number")
            try:
                number = Decimal(str(value))
            except (InvalidOperation, ValueError):
                SubmissionService._invalid_field(field, "must_be_number")
            if not number.is_finite():
                SubmissionService._invalid_field(field, "must_be_number")
            for rule, operator in (
                ("min", lambda candidate, limit: candidate < limit),
                ("max", lambda candidate, limit: candidate > limit),
            ):
                if rule not in validation:
                    continue
                try:
                    limit = Decimal(str(validation[rule]))
                except (InvalidOperation, ValueError):
                    continue
                if operator(number, limit):
                    SubmissionService._invalid_field(field, f"outside_{rule}")
            return

        allowed = SubmissionService._option_values(field)
        if field_type in {"select", "radio"}:
            if not isinstance(value, str):
                SubmissionService._invalid_field(field, "must_be_string")
            if not allowed or value not in allowed:
                SubmissionService._invalid_field(field, "invalid_option")
            return

        if field_type == "checkbox":
            if not allowed:
                if not isinstance(value, bool):
                    SubmissionService._invalid_field(field, "must_be_boolean")
                return
            if not isinstance(value, list):
                SubmissionService._invalid_field(field, "must_be_list")
            if len(value) > SubmissionService.MAX_CHECKBOX_VALUES:
                SubmissionService._invalid_field(field, "too_many_values")
            if (
                any(not isinstance(item, str) or item not in allowed for item in value)
                or len(value) != len(set(value))
            ):
                SubmissionService._invalid_field(field, "invalid_option")

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
        normalized_email = user_email.strip().lower()
        event = (
            db.query(Event)
            .filter(
                Event.uuid == event_uuid,
                Event.is_active == True,
                Event.is_deleted == False,
            )
            .first()
        )
        if not event:
            raise ActiFlowBusinessException(code=ActiFlowErrorCode.EVENT_NOT_FOUND, message="Event not found", status_code=404)

        field_map = SubmissionService._validated_field_map(
            db,
            event_uuid,
            values,
        )

        existing_submission = (
            db.query(Submission.uuid)
            .filter(
                Submission.event_uuid == event_uuid,
                func.lower(Submission.user_email) == normalized_email,
            )
            .first()
        )
        if existing_submission:
            raise ActiFlowBusinessException(
                code=ActiFlowErrorCode.ALREADY_REGISTERED,
                message="This email is already registered for the event",
                status_code=409,
            )

        if not SubmissionService.can_register(event, user_email):
            raise ActiFlowBusinessException(code=ActiFlowErrorCode.EVENT_FULL, message="Event is full or closed")

        try:
            # Create Submission
            submission = Submission(
                submission_code=generate_submission_code(event.event_code),
                event_uuid=event_uuid,
                user_email=normalized_email,
                submitted_by_uuid=submitted_by_uuid,
                status="pending",
                notes=notes,
                extra_data=extra_data or {},
                ip_address=ip_address,
                user_agent=user_agent
            )
            db.add(submission)
            # SQLAlchemy column defaults (including uuid) are assigned on
            # flush. Dependent verification/value rows need the real UUID.
            db.flush()

            # Atomic Capacity
            stmt = update(Event).where(Event.uuid == event_uuid).where(Event.status == "published").where(Event.is_active == True).where(Event.is_deleted == False).where(Event.current_attendance < Event.max_capacity).values(current_attendance=Event.current_attendance + 1)
            result = db.execute(stmt)
            if result.rowcount == 0:
                  raise ActiFlowBusinessException(code=ActiFlowErrorCode.EVENT_FULL, message="Event became full")

            # Field Values
            sub_values = [SubmissionValue(submission_uuid=submission.uuid, event_field_uuid=field_map[v.field_key].uuid, field_key=v.field_key, value=v.value) for v in values if v.field_key in field_map]
            db.add_all(sub_values)

            # Verification
            token = uuid4().hex
            verification = EmailVerification(ref_type="submission", ref_uuid=submission.uuid, email=normalized_email, token=token, expires_at=datetime.now(timezone.utc) + timedelta(minutes=30))
            db.add(verification)

            db.commit()
            db.refresh(submission)

            if background_tasks:
                background_tasks.add_task(SubmissionService.send_verification_email, normalized_email, token)

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
            "completed": ["organizer", "admin"],
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
    def update_status(db: Session, submission_uuid: UUID, target_status: str, actor_id: UUID = None, actor_role: str = "", reason: str = None, background_tasks: BackgroundTasks = None) -> Submission:
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
        SubmissionService._queue_notification(
            submission, target_status, background_tasks
        )
        return submission

    @staticmethod
    def reopen_submission(
        db: Session,
        submission_uuid: UUID,
        actor_id: UUID = None,
        actor_role: str = "",
        reason: str = None,
        background_tasks: BackgroundTasks = None,
    ) -> Submission:
        if actor_role not in {"organizer", "admin"}:
            raise ActiFlowBusinessException(
                code=ActiFlowErrorCode.UNAUTHORIZED,
                message=f"Role '{actor_role}' not allowed to reopen submissions",
                status_code=403,
            )

        submission = (
            db.query(Submission)
            .filter(Submission.uuid == submission_uuid)
            .first()
        )
        if not submission:
            raise ActiFlowBusinessException(
                code=ActiFlowErrorCode.EVENT_NOT_FOUND,
                message="Submission not found",
                status_code=404,
            )

        old_status = (
            submission.status.value
            if hasattr(submission.status, "value")
            else submission.status
        )
        target_status = "paid" if old_status == "completed" else "pending"

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
        submission.status_reason = None
        submission.notes = reason
        submission.updated_at = datetime.now(timezone.utc)

        from app.models.submission.submission_audit import SubmissionAuditLog
        db.add(
            SubmissionAuditLog(
                submission_uuid=submission_uuid,
                actor_uuid=actor_id,
                actor_role=actor_role,
                action_type="reopened",
                old_status=old_status,
                new_status=target_status,
                reason=reason,
            )
        )

        db.commit()
        db.refresh(submission)
        # Reopen notifications use the existing pending notification template,
        # including when a completed submission returns to paid review state.
        SubmissionService._queue_notification(
            submission, "pending", background_tasks
        )
        return submission

    @staticmethod
    def bulk_action(db: Session, event_uuid: UUID, submission_uuids: list[UUID], action: str, actor_id: UUID, actor_role: str, reason: str = None, background_tasks: BackgroundTasks = None) -> dict:
        ACTION_MAP = {"approve": "completed", "reject": "rejected", "reopen": "pending", "cancel": "canceled"}
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
        successful = {item for item in success_ids}
        for submission in submissions:
            if str(submission.uuid) in successful:
                SubmissionService._queue_notification(
                    submission, target_status, background_tasks
                )
        return {"success_count": len(success_ids), "fail_count": len(fail_ids), "success_ids": success_ids, "errors": errors}

    @staticmethod
    def _queue_notification(
        submission: Submission,
        target_status: str,
        background_tasks: BackgroundTasks = None,
    ) -> None:
        if background_tasks:
            background_tasks.add_task(
                send_submission_status_email,
                email=submission.user_email,
                event_name=submission.event.name,
                submission_code=submission.submission_code,
                target_status=target_status,
                reason=submission.status_reason,
                submission_uuid=str(submission.uuid),
            )
            return

    @staticmethod
    def send_verification_email(email: str, token: str):
        try:
            verify_url = (
                f"{settings.FRONTEND_BASE_URL}/verify-email"
                f"?token={token}&type=submission"
            )
            html = verification_email_html(verify_url)
            send_via_resend(to_email=email, subject="請驗證您的活動報名", html=html)
        except Exception as e:
            logger.error(f"Failed email: {e}")
