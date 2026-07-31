# app/schemas/submission/submission_mapper.py
from datetime import datetime

from app.models.submission.submission import Submission
from app.schemas.submission.submission_response import SubmissionResponse
from app.schemas.submission.submission_value import SubmissionValueResponse

def to_submission_response(s: Submission) -> SubmissionResponse:
    """
    ORM Submission -> SubmissionResponse (Organizer / Admin)

    ⚠️ 為什麼要用 mapper？
    - 避免 ORM relationship recursive serialize
    - 明確控制 response shape
    - schema 不再直接吃 ORM
    """

    return SubmissionResponse(
        uuid=s.uuid,
        event_uuid=s.event_uuid,
        submission_code=s.submission_code,
        status=s.status.value if hasattr(s.status, "value") else s.status,
        created_at=s.created_at,
        user_name=getattr(s, "user_name", None),
        user_email=getattr(s, "user_email", None),
        values=[
            SubmissionValueResponse(
                uuid=v.uuid,
                field_uuid=v.event_field_uuid,
                field_key=v.field_key,
                field_type=(
                    v.field.field_type
                    if v.field is not None
                    else None
                ),
                field_label=(
                    v.field.name
                    if v.field is not None
                    else v.field_key
                ),
                value=v.value,
                uploaded_files=[
                    f.uuid for f in (v.files or [])
                ],
            )
            for v in (s.values or [])
        ],
    )