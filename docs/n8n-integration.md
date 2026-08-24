# n8n Integration Guide

Two workflows, one at each end of an internship:

| Workflow | Trigger subject | File |
|---|---|---|
| [Application screening](#application-screening) | `CV Application` | `n8n/agentic-internship-coordinator-workflow.json` |
| [Completion review](#completion-review) | `Internship Report` | `n8n/internship-report-review-workflow.json` |

They filter on different subject lines, so neither picks up the other's mail.

---

## Application screening

Automated email-based internship screening: a candidate emails their CV, n8n
hands it to the FastAPI backend for AI evaluation, and the backend's reply is
emailed back automatically. Every processed candidate also shows up in the
dashboard.

### Flow

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

### Backend endpoint

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

### Setup steps

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

### Notes

- The Gmail Trigger filter is `subject:"CV Application" has:attachment`. Adjust
  the `q` filter if you want a different trigger.
- The PDF text is read from the `text` field produced by the **Extract from
  File** node. If your n8n version names it differently, update the `cv_text`
  expression in the Evaluate node.
- Multiple attachments: the first PDF is `attachment_0` (binary mode
  "separate"). Adjust `binaryPropertyName` if needed.


---

## Completion review

The other end: the student has finished the placement and emails three PDFs.
The backend verifies them against each other and either asks the student to
correct something or puts the package in the coordinator's queue.

### Flow

```
Student email (subject "Internship Report", 3 PDFs attached)
        │
        ▼
Gmail Trigger            ← polls every minute
        │
        ▼
Get a message            ← downloads all three attachments
        │
        ▼
Review (FastAPI)         ← POST /reports/from-n8n  (multipart, 3 × files)
        │                  backend: classify → verify → decide → email text
        ├──────────────────────────────┐
        ▼                              ▼
Reply to Student          Waiting on a coordinator?   ← status is approved/pending
                                       │
                                       ▼
                              Notify Coordinator
                                       │
                                     (stop)
```

### Two differences from the screening workflow

**No text-extraction node.** The CV flow extracts text in n8n and posts a
string. This one posts the PDFs themselves, because the backend hashes the
exact bytes it received and prints those hashes on the certificate — and
because it refuses scans that carry no extractable text. Extracting in n8n
would throw away both.

**Attachment order does not matter.** All three files go up under the same
field name, `files`. The backend reads each document to work out which is
which, so a student attaching them in any order, with any filenames, in any
language, changes nothing.

### Backend endpoint

`POST /reports/from-n8n` — `multipart/form-data`

| Field | Type | Notes |
|---|---|---|
| `intern_email` | text | Where the reply goes |
| `files` | binary × 3 | Report, evaluation form, attendance record — any order |

Response (used by both the reply node and the coordinator notification):

```json
{
  "id": "187e5032…",
  "status": "approved",
  "intern_email": "zofia@example.edu",
  "student_name": "Zofia Wiśniewska",
  "student_id": "s24187",
  "company": "Nova Logistics Software Sp. z o.o.",
  "counted_working_days": 30,
  "evaluation_score": 84,
  "report_word_count": 625,
  "max_similarity": 0.0,
  "package_sha256": "786ae655…",
  "findings": [],
  "report": "30 verified working days (240 h). …",
  "email_subject": "Internship Documents - Received and Under Review",
  "email_body": "Dear Zofia Wiśniewska, …"
}
```

`status` is one of `approved`, `pending`, `request_clarification`, `rejected`.
A held or rejected package still returns **HTTP 201** — it is a normal outcome,
not a protocol error, and n8n should not have to tell them apart.

### Setup steps

1. **Import** `n8n/internship-report-review-workflow.json`
   (Workflows → Import from File).

2. **Connect Gmail** on the three Gmail nodes — `Gmail Trigger`,
   `Get a message`, `Reply to Student`, `Notify Coordinator`. The imported
   credential is a placeholder.

3. **Set the coordinator address** in the **Notify Coordinator** node: replace
   `REPLACE_WITH_COORDINATOR_EMAIL` with the real one.

4. **Check the backend URL** in **Review (FastAPI)**. It ships pointing at
   `https://pomelo-6.codewithpeter.com/reports/from-n8n`; change the host if you
   are running elsewhere, keeping the `/reports/from-n8n` path.

5. **(Optional) Secure the webhook.** If `PDFSIGN_API_SECRET_KEY` is set on the
   backend, add Authentication → Generic → Header Auth to the Review node, with
   name `Authorization` and value `Bearer <your key>`.

6. **Activate**, then send a test email with subject **`Internship Report`** and
   three PDFs attached. Within ~1 minute the student gets a reply and the
   package appears under **Completions** in the dashboard.

### What to check on the first run

The one thing worth watching is the multipart body. n8n must send **three
separate parts all named `files`** — that is what the workflow is configured to
do, and the endpoint has been verified against exactly that shape over the wire.
If the backend answers with an `ATTACHMENT_COUNT` finding saying it received
one file instead of three, open the Review node's output and confirm all three
`formBinaryData` rows are present and that `binaryMode` is `separate` in the
workflow settings.

### Why it stops before signing

The workflow ends at notifying the coordinator. Signing is a deliberate action
in the dashboard against `POST /reports/by-id/{id}/sign`, and it stays that way
on purpose: a node that signed automatically whenever `status == "approved"`
would remove the only human from the process, leaving the university issuing
completion certificates on the strength of a regex over a PDF. See
[`report-review.md`](report-review.md).
