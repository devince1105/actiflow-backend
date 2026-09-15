# tests/conftest.py

import os
from urllib.parse import urlparse

from dotenv import dotenv_values

# Settings and the SQLAlchemy engine are created while app modules are imported.
# Force the test environment before importing any application module.
os.environ["ENV"] = "test"

env_values = dotenv_values(".env")
production_database_url = (
    os.environ.get("DATABASE_URL")
    or env_values.get("DATABASE_URL")
    or ""
)
test_database_url = (
    os.environ.get("TEST_DATABASE_URL")
    or env_values.get("TEST_DATABASE_URL")
    or ""
)


def _database_location(url: str) -> tuple[str | None, int | None, str]:
    parsed = urlparse(url)
    return parsed.hostname, parsed.port, parsed.path.lstrip("/")


HAS_ISOLATED_TEST_DATABASE = bool(
    test_database_url
    and _database_location(test_database_url)
    != _database_location(production_database_url)
)

# App imports require a syntactically valid TEST_DATABASE_URL. When no isolated
# database is configured, use a deliberately unreachable local address so model
# and unit tests can still be collected without any production fallback.
if HAS_ISOLATED_TEST_DATABASE:
    os.environ["TEST_DATABASE_URL"] = test_database_url
else:
    os.environ["TEST_DATABASE_URL"] = (
        "postgresql+psycopg2://invalid:invalid@127.0.0.1:1/actiflow_test"
    )

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.db import engine, get_db


@pytest.fixture
def db():
    if not HAS_ISOLATED_TEST_DATABASE:
        pytest.skip(
            "Database integration test skipped: configure an isolated "
            "TEST_DATABASE_URL (different host/port/database from DATABASE_URL)."
        )
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture
def client(db):
    if not HAS_ISOLATED_TEST_DATABASE:
        pytest.skip(
            "API integration test skipped: isolated TEST_DATABASE_URL missing."
        )
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        # TestClient 會保留 cookie，適合測 session/cookie auth
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
