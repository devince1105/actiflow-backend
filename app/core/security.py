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

from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
import os
from typing import Optional


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


# =================================================
# JWT Settings
# =================================================

SECRET_KEY = os.getenv("JWT_SECRET", "CHANGE_THIS_SECRET_123")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


# =================================================
# JWT: Create Token
# =================================================

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    產生 Access Token

    data payload 範例：
    {
        "sub": user.uuid,
        "role": user.role
    }
    """
    to_encode = data.copy()

    expire = datetime.utcnow() + (
        expires_delta
        if expires_delta
        else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# =================================================
# JWT: Decode Token
# =================================================

def decode_token(token: str) -> Optional[dict]:
    """
    解析 JWT
    - 成功：回傳 payload dict
    - 失敗：回傳 None
    """
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
