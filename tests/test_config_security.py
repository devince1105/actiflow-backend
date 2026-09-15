import pytest
from fastapi import Response
from pydantic import ValidationError

from app.api.auth.cookies import clear_auth_cookies, set_auth_cookie
from app.core.config import Settings
from app.core.config import settings as runtime_settings
from app.main import app


def _production_settings(**overrides):
    values = {
        "ENV": "prod",
        "DATABASE_URL": "postgresql://user:password@db.example.com/actiflow",
        "JWT_SECRET": "a-production-secret-with-at-least-32-characters",
        "COOKIE_SECURE": True,
        "FRONTEND_BASE_URL": "https://app.example.com",
        "BACKEND_CORS_ORIGINS": ["https://app.example.com"],
        "ENABLE_DEBUG_ROUTES": False,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_production_settings_accept_explicit_secure_configuration():
    settings = _production_settings()

    assert settings.ENV == "prod"
    assert settings.COOKIE_SECURE is True


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"JWT_SECRET": "change_me_please"}, "JWT_SECRET"),
        ({"COOKIE_SECURE": False}, "COOKIE_SECURE"),
        ({"BACKEND_CORS_ORIGINS": ["*"]}, "explicit allowlist"),
        ({"FRONTEND_BASE_URL": "http://app.example.com"}, "https"),
        ({"ENABLE_DEBUG_ROUTES": True}, "ENABLE_DEBUG_ROUTES"),
    ],
)
def test_production_settings_reject_unsafe_configuration(override, message):
    with pytest.raises(ValidationError, match=message):
        _production_settings(**override)


def test_samesite_none_requires_secure_cookie_in_every_environment():
    with pytest.raises(ValidationError, match="COOKIE_SECURE"):
        Settings(
            _env_file=None,
            ENV="test",
            COOKIE_SAMESITE="none",
            COOKIE_SECURE=False,
        )


def test_debug_password_reset_route_is_not_mounted_in_test_environment():
    assert not any(
        route.path == "/debug/reset-admin-password"
        for route in app.routes
    )


def test_auth_cookie_helper_uses_one_secure_policy(monkeypatch):
    monkeypatch.setattr(runtime_settings, "COOKIE_SECURE", True)
    monkeypatch.setattr(runtime_settings, "COOKIE_SAMESITE", "none")
    monkeypatch.setattr(runtime_settings, "COOKIE_DOMAIN", "example.com")

    response = Response()
    set_auth_cookie(
        response,
        key="access_token",
        value="test-token",
        max_age=60,
    )
    header = response.headers["set-cookie"]
    assert "HttpOnly" in header
    assert "Secure" in header
    assert "SameSite=none" in header
    assert "Domain=example.com" in header

    logout_response = Response()
    clear_auth_cookies(logout_response)
    delete_headers = logout_response.headers.getlist("set-cookie")
    assert len(delete_headers) == 2
    assert all("Secure" in item and "SameSite=none" in item for item in delete_headers)
