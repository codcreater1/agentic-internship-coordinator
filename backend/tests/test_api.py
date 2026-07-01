"""End-to-end API smoke tests (offline fallback mode — see conftest.py)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    body = client.get("/health").json()
    assert body["status"] == "healthy"


def test_analyze_text_returns_score():
    r = client.post(
        "/cv/analyze-text",
        json={
            "name": "Ada Lovelace",
            "email": "ada@example.com",
            "cv_text": "Python, FastAPI, Docker, PostgreSQL, REST API backend projects.",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert 0 <= data["candidate_score"] <= 100
    assert data["status"] in {"interview", "pending", "rejected"}
    assert data["email_subject"] and data["email_body"]


def test_application_is_persisted_and_listed():
    payload = {
        "name": "Bob Stone",
        "email": "bob@example.com",
        "cv_text": "No programming experience. Basic computer knowledge only.",
    }
    created = client.post("/applications/", json=payload).json()

    assert created["id"]
    assert created["status"] == "rejected"  # negative-signal CV → low score

    listing = client.get("/applications/").json()
    assert any(a["id"] == created["id"] for a in listing)

    # Newest-first ordering: index 0 is the most recent application.
    first = client.get("/applications/0").json()
    assert first["id"] == listing[0]["id"]


def test_missing_application_returns_404():
    assert client.get("/applications/9999").status_code == 404
