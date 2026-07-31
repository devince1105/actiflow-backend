from types import SimpleNamespace
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError

from app.services.media import r2_storage


class _R2Client:
    def __init__(self, metadata):
        self.metadata = metadata
        self.calls = []

    def head_object(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.metadata, Exception):
            raise self.metadata
        return self.metadata


def test_complete_avatar_upload_verifies_owned_r2_object(monkeypatch):
    user_uuid = uuid4()
    object_key = f"uploads/avatar/{user_uuid}/2026/07/avatar.webp"
    client = _R2Client(
        {
            "ContentType": "image/webp",
            "ContentLength": 1024,
        }
    )
    monkeypatch.setattr(r2_storage, "get_r2_client", lambda: client)
    monkeypatch.setattr(
        r2_storage,
        "settings",
        SimpleNamespace(
            R2_BUCKET_NAME="actiflow-media",
            R2_PUBLIC_BASE_URL="https://media.example.com",
        ),
    )

    result = r2_storage.complete_avatar_upload(
        user_uuid=user_uuid,
        object_key=object_key,
    )

    assert result == f"https://media.example.com/{object_key}"
    assert client.calls == [
        {
            "Bucket": "actiflow-media",
            "Key": object_key,
        }
    ]


def test_complete_event_cover_upload_verifies_purpose_prefix(monkeypatch):
    user_uuid = uuid4()
    object_key = f"uploads/event-cover/{user_uuid}/2026/07/cover.jpg"
    client = _R2Client(
        {
            "ContentType": "image/jpeg",
            "ContentLength": 2 * 1024 * 1024,
        }
    )
    monkeypatch.setattr(r2_storage, "get_r2_client", lambda: client)
    monkeypatch.setattr(
        r2_storage,
        "settings",
        SimpleNamespace(
            R2_BUCKET_NAME="actiflow-media",
            R2_PUBLIC_BASE_URL="https://media.example.com",
        ),
    )

    result = r2_storage.complete_image_upload(
        user_uuid=user_uuid,
        purpose=r2_storage.ImageUploadPurpose.EVENT_COVER,
        object_key=object_key,
    )

    assert result == f"https://media.example.com/{object_key}"

    with pytest.raises(ValueError, match="does not belong"):
        r2_storage.complete_image_upload(
            user_uuid=user_uuid,
            purpose=r2_storage.ImageUploadPurpose.AVATAR,
            object_key=object_key,
        )


def test_complete_avatar_upload_rejects_another_users_object():
    with pytest.raises(ValueError, match="does not belong"):
        r2_storage.complete_avatar_upload(
            user_uuid=uuid4(),
            object_key=f"uploads/avatar/{uuid4()}/2026/07/avatar.webp",
        )


def test_complete_avatar_upload_reports_missing_object(monkeypatch):
    user_uuid = uuid4()
    missing = ClientError(
        {
            "Error": {
                "Code": "404",
                "Message": "Not Found",
            }
        },
        "HeadObject",
    )
    monkeypatch.setattr(
        r2_storage,
        "get_r2_client",
        lambda: _R2Client(missing),
    )
    monkeypatch.setattr(
        r2_storage,
        "settings",
        SimpleNamespace(
            R2_BUCKET_NAME="actiflow-media",
            R2_PUBLIC_BASE_URL="https://media.example.com",
        ),
    )

    with pytest.raises(ValueError, match="was not found"):
        r2_storage.complete_avatar_upload(
            user_uuid=user_uuid,
            object_key=f"uploads/avatar/{user_uuid}/2026/07/missing.png",
        )


@pytest.mark.parametrize(
    ("metadata", "message"),
    [
        (
            {"ContentType": "text/html", "ContentLength": 1024},
            "not a supported image",
        ),
        (
            {"ContentType": "image/png", "ContentLength": 0},
            "invalid size",
        ),
        (
            {"ContentType": "image/png", "ContentLength": 6 * 1024 * 1024},
            "invalid size",
        ),
    ],
)
def test_complete_avatar_upload_rejects_invalid_metadata(
    monkeypatch,
    metadata,
    message,
):
    user_uuid = uuid4()
    monkeypatch.setattr(
        r2_storage,
        "get_r2_client",
        lambda: _R2Client(metadata),
    )
    monkeypatch.setattr(
        r2_storage,
        "settings",
        SimpleNamespace(
            R2_BUCKET_NAME="actiflow-media",
            R2_PUBLIC_BASE_URL="https://media.example.com",
        ),
    )

    with pytest.raises(ValueError, match=message):
        r2_storage.complete_avatar_upload(
            user_uuid=user_uuid,
            object_key=f"uploads/avatar/{user_uuid}/2026/07/avatar.png",
        )
