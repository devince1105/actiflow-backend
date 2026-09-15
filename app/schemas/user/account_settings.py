from datetime import date, datetime

from pydantic import BaseModel, Field


class AccountProfileResponse(BaseModel):
    email: str
    is_email_verified: bool
    auth_provider: str
    display_name: str | None = None
    phone: str | None = None
    birthday: date | None = None
    address: dict | None = None
    created_at: datetime


class AccountProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=80)
    phone: str | None = Field(default=None, max_length=30)
    birthday: date | None = None
    address: dict | None = None


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class NotificationSettingsResponse(BaseModel):
    notify_email: bool = True
    notify_sms: bool = False
    notify_marketing: bool = False


class NotificationSettingsUpdate(NotificationSettingsResponse):
    pass
