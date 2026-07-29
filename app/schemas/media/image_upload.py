from enum import Enum

from pydantic import BaseModel, Field


class ImageUploadPurpose(str, Enum):
    AVATAR = "avatar"
    EVENT_COVER = "event-cover"
    ORGANIZER_LOGO = "organizer-logo"


class ImageUploadPresignRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)
    size_bytes: int = Field(gt=0)
    purpose: ImageUploadPurpose


class ImageUploadPresignResponse(BaseModel):
    upload_url: str
    public_url: str
    object_key: str
    content_type: str
    max_size_bytes: int
    expires_in: int
