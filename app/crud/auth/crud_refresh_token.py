# src/crud/auth/crud_refresh_token.py

"""Compatibility export for the canonical refresh-token CRUD."""

from app.crud.user.crud_refresh_token import (
    CRUDRefreshToken,
    refresh_token_crud,
)

__all__ = ["CRUDRefreshToken", "refresh_token_crud"]
