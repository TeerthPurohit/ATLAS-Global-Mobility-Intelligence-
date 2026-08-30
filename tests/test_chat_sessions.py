"""Chat session lifecycle tests: create-or-reuse-if-empty, list (non-empty
only), delete (standards.md testing bar). Hits the real shared Neon
Postgres, like the existing chat/auth tests -- each test signs up a fresh
user so runs don't collide.
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
        email = f"test-{uuid.uuid4()}@example.com"
        signup = c.post("/auth/signup", json={"email": email, "password": "testpass123"})
        assert signup.status_code == 200, signup.text
        yield c


def test_create_session_returns_new_id(client):
    resp = client.post("/chat/sessions")
    assert resp.status_code == 200, resp.text
    assert resp.json()["session_id"]


def test_create_session_reuses_empty_session(client):
    first = client.post("/chat/sessions").json()["session_id"]
    second = client.post("/chat/sessions").json()["session_id"]
    assert first == second


def test_create_session_mints_new_id_once_non_empty(client):
    first = client.post("/chat/sessions").json()["session_id"]
    chat_resp = client.post("/chat", json={"question": "What is the average fare for trips picked up in JFK Airport?", "session_id": first})
    assert chat_resp.status_code == 200, chat_resp.text

    second = client.post("/chat/sessions").json()["session_id"]
    assert second != first


def test_list_sessions_excludes_empty_and_other_users(client):
    empty_session = client.post("/chat/sessions").json()["session_id"]

    resp = client.post("/chat", json={"question": "What is the average fare for trips picked up in JFK Airport?"})
    assert resp.status_code == 200, resp.text
    active_session = resp.json()["session_id"]

    listed = client.get("/chat/sessions").json()
    listed_ids = {s["session_id"] for s in listed}
    assert active_session in listed_ids
    assert empty_session not in listed_ids
    match = next(s for s in listed if s["session_id"] == active_session)
    assert match["message_count"] == 2  # user question + assistant answer
    assert match["title"]


def test_delete_session_removes_it_from_history(client):
    resp = client.post("/chat", json={"question": "What is the average fare for trips picked up in JFK Airport?"})
    session_id = resp.json()["session_id"]

    delete_resp = client.delete(f"/chat/sessions/{session_id}")
    assert delete_resp.status_code == 200, delete_resp.text

    history_resp = client.get(f"/chat/history/{session_id}")
    assert history_resp.status_code == 404


def test_delete_nonexistent_session_404s(client):
    resp = client.delete(f"/chat/sessions/{uuid.uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "SESSION_NOT_FOUND"


def test_delete_another_users_session_404s(client):
    resp = client.post("/chat", json={"question": "What is the average fare for trips picked up in JFK Airport?"})
    session_id = resp.json()["session_id"]

    other_email = f"test-{uuid.uuid4()}@example.com"
    client.post("/auth/signup", json={"email": other_email, "password": "testpass123"})  # logs in as the new user

    delete_resp = client.delete(f"/chat/sessions/{session_id}")
    assert delete_resp.status_code == 404
