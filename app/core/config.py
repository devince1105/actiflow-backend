# app/core/config.py ← 全域設定：env、常數

from functools import lru_cache
import json
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator


class Settings(BaseSettings):
    # === App Metadata ===
    APP_NAME: str = "ActiFlow Backend"
    VERSION: str = "0.1.0"
    ENV: Literal["dev", "test", "staging", "prod"]
    
    # === Database ===
    DATABASE_URL: str = ""
    TEST_DATABASE_URL: str = ""

    # === JWT ===
    JWT_SECRET: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    COOKIE_SECURE: bool = False  # HTTPS only
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    COOKIE_DOMAIN: str | None = None
    ENABLE_DEBUG_ROUTES: bool = False

    # === CORS ===
    BACKEND_CORS_ORIGINS: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:3001,http://127.0.0.1:3001"
    )

    # === Email ===
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = ""
    FRONTEND_BASE_URL: str = ""

    # === Cloudflare R2 ===
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = ""
    R2_ENDPOINT_URL: str = ""
    R2_PUBLIC_BASE_URL: str = ""

    # === Local test administrator (never expose through APIs) ===
    SUPER_ADMIN_EMAIL: str = ""
    SUPER_ADMIN_PASSWORD: str = ""

    # === Local QA role accounts (never expose through APIs) ===
    ROLE_TEST_PASSWORD: str = ""
    ROLE_TEST_ORGANIZER_UUID: str = ""
    ROLE_TEST_OWNER_EMAIL: str = ""
    ROLE_TEST_ADMIN_EMAIL: str = ""
    ROLE_TEST_MEMBER_EMAIL: str = ""
    ROLE_TEST_USER_EMAIL: str = ""

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def normalize_cors_setting(cls, v):
        if isinstance(v, list):
            return ",".join(str(item) for item in v)
        return v

    @field_validator("COOKIE_DOMAIN", mode="before")
    def empty_cookie_domain_is_none(cls, v):
        return None if v == "" else v

    @model_validator(mode="after")
    def validate_deployment_security(self):
        if self.COOKIE_SAMESITE == "none" and not self.COOKIE_SECURE:
            raise ValueError("COOKIE_SECURE must be true when COOKIE_SAMESITE=none")

        if self.ENV not in {"staging", "prod"}:
            return self

        errors: list[str] = []
        if not self.DATABASE_URL:
            errors.append("DATABASE_URL is required")
        if len(self.JWT_SECRET) < 32 or self.JWT_SECRET in {
            "change_me_please",
            "CHANGE_THIS_SECRET_123",
        }:
            errors.append("JWT_SECRET must be a non-default value of at least 32 characters")
        if not self.COOKIE_SECURE:
            errors.append("COOKIE_SECURE must be true")
        if not self.FRONTEND_BASE_URL.startswith("https://"):
            errors.append("FRONTEND_BASE_URL must use https")
        origins = self.cors_origins
        if not origins or "*" in origins:
            errors.append("BACKEND_CORS_ORIGINS must be an explicit allowlist")
        if any(not origin.startswith("https://") for origin in origins):
            errors.append("all deployment CORS origins must use https")
        if self.ENABLE_DEBUG_ROUTES:
            errors.append("ENABLE_DEBUG_ROUTES must be false")

        if errors:
            raise ValueError("Unsafe deployment configuration: " + "; ".join(errors))
        return self

    # ⭐ pydantic-settings v2 的設定寫法
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )
    
    @property
    def db_url(self) -> str:
        if self.ENV == "test":
            if not self.TEST_DATABASE_URL:
                raise RuntimeError(
                    "TEST_DATABASE_URL is required when ENV=test. "
                    "Tests must never fall back to DATABASE_URL."
                )
            return self.TEST_DATABASE_URL
        if self.ENV == "dev":
            return self.TEST_DATABASE_URL or self.DATABASE_URL
        return self.DATABASE_URL

    @property
    def cors_origins(self) -> list[str]:
        value = self.BACKEND_CORS_ORIGINS.strip()
        if not value:
            return []
        if value.startswith("["):
            decoded = json.loads(value)
            if not isinstance(decoded, list):
                raise ValueError("BACKEND_CORS_ORIGINS JSON must be a list")
            return [str(item).strip() for item in decoded if str(item).strip()]
        return [item.strip() for item in value.split(",") if item.strip()]


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
