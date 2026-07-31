# app/core/exceptions.py ← 自定義 Exception

from enum import Enum
from typing import Any, Optional

class ActiFlowErrorCode(str, Enum):
    EVENT_NOT_FOUND = "EVENT_NOT_FOUND"
    EVENT_NOT_PUBLISHED = "EVENT_NOT_PUBLISHED"
    EVENT_FULL = "EVENT_FULL"
    ALREADY_REGISTERED = "ALREADY_REGISTERED"
    EMAIL_NOT_VERIFIED = "EMAIL_NOT_VERIFIED"
    INVALID_STATUS = "INVALID_STATUS"
    INVALID_STATUS_TRANSITION = "INVALID_STATUS_TRANSITION"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"

class ActiFlowBusinessException(Exception):
    def __init__(
        self,
        code: ActiFlowErrorCode,
        message: str,
        status_code: int = 400,
        detail: Optional[Any] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)
