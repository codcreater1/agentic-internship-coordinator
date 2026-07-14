"""End-to-end API smoke tests (offline fallback mode — see conftest.py)."""

import io

import fitz
from fastapi.testclient import TestClient
from PIL import Image

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


def test_sign_pdf_download_url_is_reachable():
    """Regression test: /pdf/sign previously returned a download_url prefixed
    with settings.api_prefix ("/api/v1/pdf/download/..."), but routers are
    mounted in app.main without that prefix, so the real route lives at
    "/pdf/download/...". The mismatch made every generated download link
    404. This test fails again if that prefix mismatch is reintroduced.
    """
    doc = fitz.open()
    doc.new_page()
    pdf_buf = io.BytesIO()
    doc.save(pdf_buf)
    pdf_buf.seek(0)

    upload = client.post(
        "/pdf/upload",
        files={"file": ("sample.pdf", pdf_buf, "application/pdf")},
    )
    assert upload.status_code == 201
    task_id = upload.json()["task_id"]

    img = Image.new("RGBA", (50, 20), (255, 0, 0, 255))
    img_buf = io.BytesIO()
    img.save(img_buf, format="PNG")
    img_buf.seek(0)

    signed = client.post(
        "/pdf/sign",
        data={"task_id": task_id, "page": 0, "x": 10, "y": 10, "w": 50, "h": 20},
        files={"image": ("sig.png", img_buf, "image/png")},
    )
    assert signed.status_code == 200
    download_url = signed.json()["download_url"]

    assert download_url.startswith("/pdf/download/"), download_url

    download = client.get(download_url)
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/pdf"
