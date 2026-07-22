"""End-to-end API smoke tests (offline fallback mode — see conftest.py)."""

import io
from pathlib import Path

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
        # A complete application by default; tests that exercise the
        # mandatory-field gate blank these out explicitly.
        "company_name": "Acme GmbH",
        "supervisor_name": "Grace Hopper",
        "supervisor_contact": "grace@acme.example",
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


def _patch_graph(monkeypatch, **overrides):
    monkeypatch.setattr(
        application_service, "graph",
        type("G", (), {"invoke": staticmethod(
            lambda _s: _fake_graph_result(**overrides))})(),
    )


def test_missing_supervisor_holds_application_for_clarification(monkeypatch):
    """Mandatory-field gate: an interview-worthy candidate whose application
    does not name a workplace supervisor must be held for clarification, not
    advanced to interview — the agreement names that supervisor."""
    _patch_graph(monkeypatch, supervisor_name="", supervisor_contact="")

    result = ApplicationService.evaluate("cv", candidate_name="Ada")

    assert result["candidate_score"] == 85          # merit is unaffected
    assert result["status"] == "request_clarification"
    assert result["missing_fields"] == ["supervisor_name", "supervisor_contact"]


def test_clarification_email_names_every_missing_detail(monkeypatch):
    """The candidate can only fix what they are told about."""
    _patch_graph(monkeypatch, company_name="", supervisor_name="")

    result = ApplicationService.evaluate("cv", candidate_name="Ada")
    body = result["email_body"].lower()

    assert "host company" in body or "organisation" in body
    assert "supervisor" in body


def test_no_contract_when_placement_details_are_missing(monkeypatch):
    """End-to-end regression for the reported defect: the workflow used to run
    on to contract generation even with mandatory fields empty. A held
    application must reach the dashboard with no agreement attached."""
    _patch_graph(monkeypatch, supervisor_name="", supervisor_contact="")

    created = client.post("/applications/", json={
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "cv_text": "Python, FastAPI, Docker, PostgreSQL backend projects.",
    }).json()

    assert created["status"] == "request_clarification"
    assert created["contract_pdf_path"] is None
    assert created["contract_task_id"] is None
    assert "supervisor_name" in created["missing_fields"]


def test_contract_is_generated_for_a_complete_application(monkeypatch):
    """The gate must not block a complete application."""
    _patch_graph(monkeypatch)

    created = client.post("/applications/", json={
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "cv_text": "Python, FastAPI, Docker, PostgreSQL backend projects.",
    }).json()

    assert created["status"] == "interview"
    assert created["contract_task_id"]
    assert created["missing_fields"] == []
    assert Path(created["contract_pdf_path"]).is_file()


def test_web_upload_panel_also_refuses_incomplete_applications(monkeypatch):
    """/cv/analyze-text is the second contract entry point (the upload panel);
    it must enforce the same gate as the email/n8n route."""
    _patch_graph(monkeypatch, company_name="")

    data = client.post("/cv/analyze-text", json={
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "cv_text": "Python, FastAPI, Docker, PostgreSQL backend projects.",
    }).json()

    assert data["status"] == "request_clarification"
    assert data["contract_task_id"] is None


def test_contract_service_refuses_to_render_without_supervisor(tmp_path):
    """Defence in depth: even called directly, the agreement cannot be produced
    with a blank supervisor — a signable document with missing parties is worse
    than a loud failure."""
    import pytest

    from app.services.contract_service import ContractService

    with pytest.raises(ValueError, match="workplace supervisor"):
        ContractService.create_contract_pdf(
            name="Ada Lovelace", email="ada@example.com",
            recommended_role="Backend Developer Internship",
            candidate_score=85,
            company_name="Acme GmbH", supervisor_name="", supervisor_contact="x@y.z",
            output_path=tmp_path / "contract.pdf",
        )


def test_ineligible_placement_stays_rejected_not_clarification(monkeypatch):
    """Gate ordering: a non-EU placement is refused outright — we do not ask a
    candidate for a supervisor we would never contract with."""
    _patch_graph(monkeypatch, internship_country="Turkey",
                 internship_eu_eligible="non_eu",
                 supervisor_name="", supervisor_contact="")

    assert ApplicationService.evaluate("cv")["status"] == "rejected"


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
    assert data["status"] in {
        "interview", "pending", "rejected", "request_clarification",
    }
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


def test_signature_date_is_stamped_at_signing_not_generation(tmp_path):
    """The date beside the signature must be the date the coordinator signed.

    It used to be printed by create_contract_pdf, i.e. when the contract was
    generated — often days before signing — so a contract signed on the 21st
    still showed the 16th. Generation must leave it blank; signing stamps it.
    """
    from datetime import datetime, timezone

    from app.services.contract_service import SIGNATURE_DATE_POS, ContractService
    from app.services.pdf_service import pdf_service

    unsigned = tmp_path / "contract.pdf"
    ContractService.create_contract_pdf(
        name="Ada Lovelace", email="ada@example.com",
        recommended_role="Backend Developer Internship",
        candidate_score=80,
        company_name="Acme GmbH", supervisor_name="Grace Hopper",
        supervisor_contact="grace@acme.example",
        output_path=unsigned,
    )

    today = datetime.now(timezone.utc).date().isoformat()
    unsigned_text = fitz.open(str(unsigned))[0].get_text()
    # Only the header "Date:" field carries a date before signing.
    assert unsigned_text.count(today) == 1

    img = Image.new("RGBA", (60, 25), (0, 0, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    signed = tmp_path / "signed.pdf"
    pdf_service.embed_signature(
        source_pdf=unsigned, output_pdf=signed, image_bytes=buf.getvalue(),
        page_index=0, x=70, y=600, w=220, h=70,
        text_stamps=[(today, *SIGNATURE_DATE_POS)],
    )

    signed_text = fitz.open(str(signed))[0].get_text()
    assert signed_text.count(today) == 2      # header + signing date
