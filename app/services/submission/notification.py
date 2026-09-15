import logging

from app.api.utils.email_mailer import send_generic_email
from app.api.utils.email_templates import (
    submission_canceled_email,
    submission_completed_email,
    submission_email_verified_email,
    submission_rejected_email,
    submission_reopened_email,
)
from app.core.config import settings
from app.models.submission.submission import Submission


logger = logging.getLogger("actiflow.submission.notifications")


def send_submission_status_notification(
    submission: Submission,
    target_status: str,
) -> None:
    """Send a committed status notification without affecting the transaction."""
    send_submission_status_email(
        email=submission.user_email,
        event_name=submission.event.name,
        submission_code=submission.submission_code,
        target_status=target_status,
        reason=submission.status_reason,
        submission_uuid=str(submission.uuid),
    )


def send_submission_status_email(
    *,
    email: str,
    event_name: str,
    submission_code: str,
    target_status: str,
    reason: str | None = None,
    submission_uuid: str | None = None,
) -> None:
    try:
        if not email:
            return
        common = {
            "project_name": getattr(settings, "PROJECT_NAME", "ActiFlow"),
            "event_name": event_name,
            "submission_code": submission_code,
        }
        if target_status == "email_verified":
            subject, body = submission_email_verified_email(**common)
        elif target_status == "completed":
            subject, body = submission_completed_email(**common)
        elif target_status == "rejected":
            subject, body = submission_rejected_email(
                **common,
                reason=reason or "未提供具體原因",
            )
        elif target_status == "canceled":
            subject, body = submission_canceled_email(**common)
        elif target_status == "pending":
            subject, body = submission_reopened_email(
                **common,
                note=reason or "請登入系統查看最新狀態",
            )
        else:
            return

        send_generic_email(
            to_email=email,
            subject=subject,
            html=body,
        )
    except Exception:
        logger.exception(
            "Failed to send submission status notification",
            extra={
                "submission_uuid": submission_uuid,
                "target_status": target_status,
            },
        )


# Compatibility wrappers for legacy command routes.
def notify_submission_rejected(*, db, submission: Submission) -> None:
    send_submission_status_notification(submission, "rejected")


def notify_submission_reopened(*, db, submission: Submission) -> None:
    send_submission_status_notification(submission, "pending")


def notify_submission_completed(*, db, submission: Submission) -> None:
    send_submission_status_notification(submission, "completed")
