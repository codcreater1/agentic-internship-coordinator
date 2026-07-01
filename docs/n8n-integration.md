# n8n Integration Guide

Automated email-based internship screening: a candidate emails their CV, n8n
hands it to the FastAPI backend for AI evaluation, and the backend's reply is
emailed back automatically. Every processed candidate also shows up in the
dashboard.

## Flow

```
Candidate email (subject "CV Application", PDF attached)
        │
        ▼
Gmail Trigger            ← polls every minute
        │
        ▼
Get a message            ← downloads the PDF attachment
        │
        ▼
Extract PDF Text         ← PDF → plain text (n8n "Extract from File")
        │
        ▼
Evaluate (FastAPI)       ← POST /applications/from-n8n  {name, email, cv_text}
        │                  backend: score → status → personalized email
        ▼
Reply to Candidate       ← Gmail send using email_subject / email_body
```

The backend decides the outcome (interview / pending / rejected) **and writes
the email text**, so n8n does not need any If/branch node — it just delivers
whatever the backend returns. This also means "pending" candidates get the
correct under-review email (the old score-only branch sent them a rejection).

## Backend endpoint

`POST /applications/from-n8n`

Request (JSON):
```json
{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "cv_text": "Python, FastAPI, Docker, PostgreSQL ..."
}
```

Response (used by the Gmail reply node):
```json
{
  "id": "….",
  "name": "Jane Doe",
  "email": "jane@example.com",
  "candidate_score": 82,
  "recommended_role": "Backend Developer Internship",
  "status": "interview",
  "report": "…",
  "email_subject": "…",
  "email_body": "…"
}
```

The application is persisted (SQLite) and appears in the dashboard immediately.

## Setup steps

1. **Run the backend** (with your Anthropic key in `backend/.env` for real AI):
   ```bash
   cd backend
   uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

2. **Expose it publicly** so n8n (cloud or another machine) can reach it:
   ```bash
   ngrok http 8000
   ```
   Copy the `https://…ngrok-free.app` URL.

3. **Import the workflow** `n8n/agentic-internship-coordinator-workflow.json`
   into n8n (Workflows → Import from File).

4. **Connect Gmail** on the three Gmail nodes (`Gmail Trigger`,
   `Get a message`, `Reply to Candidate`): select/create your Gmail OAuth2
   credential. (The imported credential is a placeholder.)

5. **Set the backend URL** in the **Evaluate (FastAPI)** node — replace
   `https://YOUR-NGROK-SUBDOMAIN.ngrok-free.app` with your ngrok URL, keeping
   the `/applications/from-n8n` path.

6. **(Optional) Secure the webhook.** If you set `PDFSIGN_API_SECRET_KEY` in
   `backend/.env`, add a header to the Evaluate node:
   `Authorization: Bearer <your key>` (enable "Send Headers" → add the header).

7. **Activate** the workflow. Send a test email to the connected inbox with
   subject **`CV Application`** and a PDF CV attached. Within ~1 minute the
   candidate receives the AI reply and the case appears in the dashboard.

## Notes

- The Gmail Trigger filter is `subject:"CV Application" has:attachment`. Adjust
  the `q` filter if you want a different trigger.
- The PDF text is read from the `text` field produced by the **Extract from
  File** node. If your n8n version names it differently, update the `cv_text`
  expression in the Evaluate node.
- Multiple attachments: the first PDF is `attachment_0` (binary mode
  "separate"). Adjust `binaryPropertyName` if needed.
