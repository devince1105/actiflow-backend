# app/core/security.py
# -------------------------------------------------
# Security Core
# - Password hash / verify
# - JWT create / decode
# -------------------------------------------------
# ❗此檔案不得依賴：
#   - DB
#   - CRUD
#   - FastAPI Depends
#   - Models
# -------------------------------------------------

from passlib.context import CryptContext


# =================================================
# Password Hash / Verify
# =================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
    """將明碼密碼 Hash 成 bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """驗證明碼與 Hash 是否相符"""
    return pwd_context.verify(plain_password, hashed_password)
