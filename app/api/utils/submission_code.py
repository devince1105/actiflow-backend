# app/api/utils/submission_code.py

from datetime import datetime
from uuid import uuid4


def generate_submission_code(event_code: str) -> str:
    """
    Generate a readable code with enough entropy for concurrent submissions.

    Example: EVT-20251224-20260914094530123456-A1B2C3D4
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    nonce = uuid4().hex[:8].upper()
    return f"{event_code}-{timestamp}-{nonce}"
