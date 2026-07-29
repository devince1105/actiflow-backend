from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from urllib.parse import quote
from uuid import UUID, uuid4

import boto3

from app.core.config import settings
from app.schemas.media.image_upload import ImageUploadPurpose


ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

MAX_IMAGE_SIZE_BY_PURPOSE = {
    ImageUploadPurpose.AVATAR: 5 * 1024 * 1024,
    ImageUploadPurpose.EVENT_COVER: 8 * 1024 * 1024,
    ImageUploadPurpose.ORGANIZER_LOGO: 5 * 1024 * 1024,
}

PRESIGNED_URL_EXPIRES_IN = 5 * 60


def validate_r2_settings() -> None:
    required = {
        "R2_ACCESS_KEY_ID": settings.R2_ACCESS_KEY_ID,
        "R2_SECRET_ACCESS_KEY": settings.R2_SECRET_ACCESS_KEY,
        "R2_BUCKET_NAME": settings.R2_BUCKET_NAME,
        "R2_ENDPOINT_URL": settings.R2_ENDPOINT_URL,
        "R2_PUBLIC_BASE_URL": settings.R2_PUBLIC_BASE_URL,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(f"Missing R2 settings: {', '.join(missing)}")


@lru_cache
def get_r2_client():
    validate_r2_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.R2_ENDPOINT_URL.rstrip("/"),
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


def create_image_upload(
    *,
    user_uuid: UUID,
    purpose: ImageUploadPurpose,
    content_type: str,
    size_bytes: int,
) -> dict:
    extension = ALLOWED_IMAGE_TYPES.get(content_type)
    if not extension:
        raise ValueError("Unsupported image type")

    max_size = MAX_IMAGE_SIZE_BY_PURPOSE[purpose]
    if size_bytes > max_size:
        raise ValueError(f"Image exceeds the {max_size} byte limit")

    date_path = datetime.now().strftime("%Y/%m")
    object_key = (
        f"uploads/{purpose.value}/{user_uuid}/{date_path}/{uuid4().hex}{extension}"
    )
    client = get_r2_client()
    upload_url = client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.R2_BUCKET_NAME,
            "Key": object_key,
            "ContentType": content_type,
            "ContentLength": size_bytes,
        },
        ExpiresIn=PRESIGNED_URL_EXPIRES_IN,
    )
    public_url = (
        f"{settings.R2_PUBLIC_BASE_URL.rstrip('/')}/{quote(object_key)}"
    )

    return {
        "upload_url": upload_url,
        "public_url": public_url,
        "object_key": object_key,
        "content_type": content_type,
        "max_size_bytes": max_size,
        "expires_in": PRESIGNED_URL_EXPIRES_IN,
    }
