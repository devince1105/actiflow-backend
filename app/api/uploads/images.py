from fastapi import APIRouter, Depends, HTTPException

from app.api.auth.dependencies import get_current_user_obj
from app.models.user.user import User
from app.schemas.media.image_upload import (
    ImageUploadPresignRequest,
    ImageUploadPresignResponse,
)
from app.services.media.r2_storage import create_image_upload


router = APIRouter(
    prefix="/uploads/images",
    tags=["Uploads - Images"],
)


@router.post(
    "/presign",
    response_model=ImageUploadPresignResponse,
    summary="建立 R2 圖片直傳網址",
)
def presign_image_upload(
    data: ImageUploadPresignRequest,
    current_user: User = Depends(get_current_user_obj),
):
    try:
        return create_image_upload(
            user_uuid=current_user.uuid,
            purpose=data.purpose,
            content_type=data.content_type,
            size_bytes=data.size_bytes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail="Media storage is not configured",
        ) from exc
