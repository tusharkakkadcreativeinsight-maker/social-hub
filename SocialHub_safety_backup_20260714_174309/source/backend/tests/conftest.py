"""Pytest configuration and fixtures for SocialHub tests.

This module provides:
- Automatic database table creation before tests run
- Isolated test database per test session
- Fixtures for authenticated users, posts, and other models
- Clean teardown after tests complete
"""

import os
import sys
import shutil
import tempfile
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from collections.abc import Generator

# Add backend to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Set environment to testing mode
os.environ["DEBUG"] = "true"
os.environ["TESTING"] = "true"
os.environ["SEED_DEMO_ACCOUNTS"] = "false"
test_root = os.path.join(tempfile.gettempdir(), f"socialhub_pytest_{uuid.uuid4().hex}")
os.makedirs(test_root, exist_ok=True)
test_db_path = os.path.join(test_root, "socialhub_test.db")
test_db_url_path = test_db_path.replace(os.sep, "/")
os.environ["DATABASE_URL"] = f"sqlite:///{test_db_url_path}"
os.environ["DATABASE_URL_ASYNC"] = f"sqlite+aiosqlite:///{test_db_url_path}"
os.environ["UPLOAD_DIR"] = os.path.join(test_root, "uploads")

# Import after path setup
from app.database import Base, engine, SessionLocal
from app.models import models  # noqa: F401 - registers all models with Base.metadata
from main import app, ensure_schema_compatibility


def pytest_sessionstart(session):
    """Ensure API tests never depend on manually running backend/test_db.py.

    Pytest imports test modules during collection; some tests create a module-level
    TestClient, so table creation must happen before the first request and not
    only inside a fixture body.
    """
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility()


@pytest.fixture(scope="session", autouse=True)
def setup_test_database() -> Generator[None, None, None]:
    """Create all tables at the start of the test session.
    
    This fixture runs once per test session and creates all database tables
    defined in app.models.models before any tests run.
    """
    # Idempotent safety net for direct/partial pytest runs.
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility()
    
    yield
    
    # Optional: Clean up after all tests (comment out if you want to inspect DB)
    # Base.metadata.drop_all(bind=engine)
    shutil.rmtree(test_root, ignore_errors=True)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide a clean database session for each test.
    
    Each test gets its own session that is rolled back after the test,
    ensuring test isolation.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client() -> TestClient:
    """Provide a test client for making HTTP requests to the app."""
    return TestClient(app)


@pytest.fixture
def auth_headers(client: TestClient) -> dict:
    """Create a test user and return authorization headers."""
    import uuid
    
    unique = uuid.uuid4().hex[:10]
    user_data = {
        "email": f"test_{unique}@example.com",
        "username": f"testuser_{unique}",
        "password": "TestPass123!",
        "full_name": "Test User",
    }
    
    # Register user
    response = client.post("/api/auth/register", json=user_data)
    assert response.status_code == 201, f"Failed to register: {response.text}"
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def authenticated_client(client: TestClient, auth_headers: dict) -> TestClient:
    """Provide a test client with authenticated headers."""
    client.headers.update(auth_headers)
    return client
