from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, HttpUrl


class AdminSystemSettingsResponse(BaseModel):
    uuid: UUID | None = None
    site_name: str = "ActiFlow"
    logo_url: str | None = None
    support_email: str | None = None
    maintenance_mode: bool = False
    registration_enabled: bool = True
    organizer_applications_enabled: bool = True
    default_event_capacity: int = 100
    max_image_size_mb: int = 5
    version: int = 0


class AdminSystemSettingsUpdate(BaseModel):
    expected_version: int = Field(ge=0)
    site_name: str | None = Field(default=None, min_length=1, max_length=255)
    logo_url: HttpUrl | None = None
    support_email: EmailStr | None = None
    maintenance_mode: bool | None = None
    registration_enabled: bool | None = None
    organizer_applications_enabled: bool | None = None
    default_event_capacity: int | None = Field(default=None, ge=1, le=100000)
    max_image_size_mb: int | None = Field(default=None, ge=1, le=20)
