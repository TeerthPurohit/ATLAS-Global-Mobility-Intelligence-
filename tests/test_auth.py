"""Auth flow tests: signup, login, /me, logout (standards.md testing bar).
Hits the real shared Neon Postgres, like the existing chat tests in
test_api.py -- each test uses a fresh random email so runs don't collide.
"""

import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.main import app  # noqa: E402

WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "nyc_rides.duckdb"

pytestmark = pytest.mark.skipif(not WAREHOUSE_PATH.exists(), reason="warehouse not built")


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _unique_email() -> str:
    return f"test-{uuid.uuid4()}@example.com"


def test_signup_then_me(client):
    email = _unique_email()
    resp = client.post("/auth/signup", json={"email": email, "password": "testpass123"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["email"] == email
    assert "session_token" in resp.cookies

    me_resp = client.get("/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == email


def test_signup_duplicate_email_rejected(client):
    email = _unique_email()
    first = client.post("/auth/signup", json={"email": email, "password": "testpass123"})
    assert first.status_code == 200

    second = client.post("/auth/signup", json={"email": email, "password": "anotherpass123"})
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "AUTH_EMAIL_TAKEN"


def test_login_wrong_password_rejected(client):
    email = _unique_email()
    client.post("/auth/signup", json={"email": email, "password": "testpass123"})
    client.post("/auth/logout")

    resp = client.post("/auth/login", json={"email": email, "password": "wrongpassword"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"


def test_me_without_cookie_unauthenticated(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTH_NOT_AUTHENTICATED"


def test_logout_then_me_unauthenticated(client):
    email = _unique_email()
    client.post("/auth/signup", json={"email": email, "password": "testpass123"})

    logout_resp = client.post("/auth/logout")
    assert logout_resp.status_code == 200

    me_resp = client.get("/auth/me")
    assert me_resp.status_code == 401
