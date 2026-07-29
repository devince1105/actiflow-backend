# tests/conftest.py

import os

# Settings and the SQLAlchemy engine are created while app modules are imported.
# Force the test environment before importing any application module.
os.environ["ENV"] = "test"

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.db import SessionLocal


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
        session.rollback()
    finally:
        session.close()


@pytest.fixture
def client():
    # TestClient 會保留 cookie，適合測 session/cookie auth
    return TestClient(app)
