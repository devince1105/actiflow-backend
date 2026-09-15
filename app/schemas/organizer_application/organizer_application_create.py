# app/schemas/organizer_application/organizer_application_create.py

from pydantic import BaseModel, EmailStr, Field, HttpUrl


class OrganizerApplicationCreate(BaseModel):
    """
    User 發起申請建立新 Organizer。
    user_uuid 由後端從 JWT / auth.me 取得，不由前端傳入。
    """

    name: str = Field(min_length=2, max_length=150)
    description: str = Field(min_length=20, max_length=2000)
    reason: str = Field(min_length=20, max_length=2000)
    contact_email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    website: HttpUrl | None = None
    address: str | None = Field(default=None, max_length=500)

    model_config = {"from_attributes": True}
