# app/api/auth/dependencies.py
# -------------------------------------------------
# Auth Dependencies
# - Unified current user resolver
# - Cookie-based JWT authentication
# -------------------------------------------------

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.jwt import decode_access_token
from app.models.user.user import User
from app.api.auth.identity import build_identity


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """
    Unified auth dependency.

    - Read access_token from cookie
    - Decode JWT
    - Load User from DB
    - Return identity dict (compatible with /auth/me)
    """

    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = decode_access_token(access_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_uuid = payload.get("sub")
    if not user_uuid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = (
        db.query(User)
        .filter(
            User.uuid == user_uuid,
            User.is_deleted == False,
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return build_identity(db, user)


def get_current_user_uuid(request: Request) -> str:
    """Decode only the authenticated user UUID without querying the database.

    Resource-specific dependencies must still verify the user and permission
    against the database. This avoids building every membership when an API
    only needs one organizer-scoped membership.
    """
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = decode_access_token(access_token)
    user_uuid = payload.get("sub") if payload else None
    if not user_uuid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return user_uuid


def get_current_user_obj(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """
    Get current user as ORM object (for internal use)
    """
    access_token = request.cookies.get("access_token")
    if not access_token:
        # Check Header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            access_token = auth_header.split(" ")[1]

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = decode_access_token(access_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_uuid = payload.get("sub")
    if not user_uuid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = (
        db.query(User)
        .filter(
            User.uuid == user_uuid,
            User.is_deleted == False,
            User.is_active == True,
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user
