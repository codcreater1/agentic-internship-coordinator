"""End-to-end API smoke tests (offline fallback mode — see conftest.py)."""

import io

import fitz
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.services import application_service
from app.services.application_service import ApplicationService

client = TestClient(app)


def _fake_graph_result(**overrides):
    base = {
        "extracted_name": "Ada Lovelace",
        "candidate_score": 85,
        "recommendation": "Backend Developer Internship",
        "report": "Strong candidate.",
        "strengths": ["Python"],
        "weaknesses": [],
        "internship_country": "",
        "internship_eu_eligible": "unknown",
    }
    base.update(overrides)
    return base


def test_non_eu_placement_is_rejected_regardless_of_score(monkeypatch):
    """Eligibility gate: a strong candidate (85) whose internship placement is
    outside the EU/EEA must be rejected, not sent to interview."""
    monkeypatch.setattr(
        application_service, "graph",
        type("G", (), {"invoke": staticmethod(
            lambda _s: _fake_graph_result(internship_country="Turkey",
                                          internship_eu_eligible="non_eu"))})(),
    )
    result = ApplicationService.evaluate("cv", candidate_name="Ada")
    assert result["candidate_score"] == 85
    assert result["status"] == "rejected"


def test_eu_placement_high_score_reaches_interview(monkeypatch):
    monkeypatch.setattr(
        application_service, "graph",
        type("G", (), {"invoke": staticmethod(
            lambda _s: _fake_graph_result(internship_country="Poland",
                                          internship_eu_eligible="eu"))})(),
    )
    assert ApplicationService.evaluate("cv", candidate_name="Ada")["status"] == "interview"


def test_unknown_placement_does_not_block(monkeypatch):
    """A plain CV with no stated placement (unknown) must not be blocked."""
    monkeypatch.setattr(
        application_service, "graph",
        type("G", (), {"invoke": staticmethod(
            lambda _s: _fake_graph_result(internship_eu_eligible="unknown"))})(),
    )
    assert ApplicationService.evaluate("cv", candidate_name="Ada")["status"] == "interview"


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


def _upload_and_sign() -> str:
    """Upload a blank PDF, sign it, and return the download URL."""
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
    return signed.json()["download_url"]


def test_signed_contract_survives_download():
    """Regression test: /pdf/download used to schedule remove_task() as a
    background task, wiping the whole task directory the first time the file was
    fetched. The dashboard opens that link automatically right after signing, so
    a signed internship agreement — which is previewed, re-downloaded and
    emailed to the candidate — was destroyed on first download. Downloading
    twice must keep working.
    """
    download_url = _upload_and_sign()

    assert client.get(download_url).status_code == 200
    # The file must still be there for the preview / email / re-download paths.
    assert client.get(download_url).status_code == 200


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
