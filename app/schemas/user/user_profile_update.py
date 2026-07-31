# app/schemas/user/user_profile_update.py

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class UserProfileUpdate(BaseModel):
    birthday: datetime | None = None
    address: dict[str, Any] | None = None
    school: str | None = None
    employment: str | None = None
    job_title: str | None = None
    blood_type: str | None = None
