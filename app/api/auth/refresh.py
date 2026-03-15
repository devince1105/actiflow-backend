# app/api/auth/refresh.py

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.jwt import create_access_token
from app.models.user.user import User
from app.crud.auth.crud_refresh_token import refresh_token_crud

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
    db_token = refresh_token_crud.get_by_token(db, refresh_token)
    if not db_token:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # 3. 用 user_uuid 找 User
    user = (
        db.query(User)
        .filter(User.uuid == db_token.user_uuid)
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

    # 5. 回寫 cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,  # local dev
        max_age=60 * 15,
    )

    return {
        "success": True,
        "access_token": access_token,
        "user": {
            "uuid": str(user.uuid),
            "email": user.email,
        },
    }
