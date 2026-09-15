# app/api/auth/logout.py

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.auth.cookies import REFRESH_COOKIE, clear_auth_cookies
from app.core.db import get_db
from app.crud.user.crud_refresh_token import refresh_token_crud

router = APIRouter()


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    登出：清除 access_token、refresh_token Cookie
    """

    token_value = request.cookies.get(REFRESH_COOKIE)
    if token_value:
        token = refresh_token_crud.get_by_token(db, token_value)
        if token and not token.revoked:
            refresh_token_crud.revoke(db, token)

    clear_auth_cookies(response)

    return {"message": "Logged out successfully"}
