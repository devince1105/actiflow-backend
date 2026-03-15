# src/crud/auth/crud_refresh_token.py

from sqlalchemy.orm import Session

from app.crud.base.crud_base import CRUDBase
from app.models.auth.refresh_token import RefreshToken


class CRUDRefreshToken(CRUDBase[RefreshToken]):

    def get_by_token(self, db: Session, token: str) -> RefreshToken | None:
        return (
            db.query(self.model)
            .filter(self.model.token == token)
            .first()
        )


# ============================================================
# ⭐ CRUD instance（一定要有）
# ============================================================
refresh_token_crud = CRUDRefreshToken(RefreshToken)
