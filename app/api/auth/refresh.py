# app/api/auth/refresh.py

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.jwt import create_access_token
from app.core.config import settings
from app.models.user.user import User
from app.crud.user.crud_refresh_token import refresh_token_crud
from app.api.auth.cookies import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    set_auth_cookie,
)

router = APIRouter(tags=["Auth"])


@router.post("/refresh")
def refresh_access_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    # 1. 從 cookie 取 refresh_token
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    # 2. 查 refresh token
    db_token = refresh_token_crud.get_valid_token(db, refresh_token)
    if not db_token:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # 3. 用 user_uuid 找 User
    user = (
        db.query(User)
        .filter(
            User.uuid == db_token.user_uuid,
            User.is_active == True,
            User.is_deleted == False,
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # 4. 建立新的 access token
    access_token = create_access_token(
        {
            "sub": str(user.uuid),
        }
    )

    replacement = refresh_token_crud.rotate(
        db,
        current_token=db_token,
        user_agent=request.headers.get("User-Agent", "unknown"),
    )

    # 5. 回寫 cookies
    set_auth_cookie(
        response,
        key=ACCESS_COOKIE,
        value=access_token,
        max_age=60 * settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    set_auth_cookie(
        response,
        key=REFRESH_COOKIE,
        value=replacement.token,
        max_age=60 * 60 * 24 * settings.REFRESH_TOKEN_EXPIRE_DAYS,
    )

    return {
        "success": True,
        "user": {
            "uuid": str(user.uuid),
            "email": user.email,
        },
    }
