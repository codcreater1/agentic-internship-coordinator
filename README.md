# 🤖 Agentic Internship Coordinator

An AI-powered internship application screening system that automatically processes CVs, evaluates candidates, and sends interview or rejection emails.

---

## 🚀 Features

- 📄 Automatic PDF CV processing
- 🤖 AI-powered CV evaluation
- 📊 Candidate scoring
- 💼 Internship role recommendation
- 📧 Automatic interview invitation emails
- ❌ Automatic rejection emails
- ⚡ End-to-end workflow automation with n8n
- 🌐 FastAPI backend
- 🧠 LangGraph AI workflow

---

## 🏗️ Architecture

```
Candidate
    │
    ▼
Gmail
    │
    ▼
n8n Gmail Trigger
    │
    ▼
Download PDF Attachment
    │
    ▼
FastAPI Backend
    │
    ▼
PDF Text Extraction
    │
    ▼
LangGraph AI Analysis
    │
    ▼
Candidate Score
    │
    ▼
Interview / Rejected Decision
    │
    ▼
Automatic Email Response
```

---

## 🛠️ Technologies

- Python
- FastAPI
- LangGraph
- LLM evaluation via any OpenAI-compatible API (Groq / Gemini free tier)
- React + Vite (frontend)
- n8n
- Gmail API
- PDF Processing
- REST API
- GitHub

---

## 📂 Project Structure

```
backend/
frontend/
docs/
n8n/
README.md
```

---

## ⚙️ Workflow

1. Candidate sends a CV (PDF) by email.
2. Gmail Trigger detects the new application.
3. The PDF attachment is downloaded automatically.
4. FastAPI extracts text from the CV.
5. LangGraph evaluates the candidate.
6. A candidate score is generated.
7. The system decides:
   - Interview Invitation
   - Rejected
8. An automatic email is sent to the candidate.

---

## ▶️ Running the Project

### Backend

```bash
cd backend
pip install -r requirements.txt
```

Edit `backend/.env` (already scaffolded; copy from `.env.example` if missing)
and set a **free** API key so the AI evaluation is enabled:

```bash
# Get a free key at https://aistudio.google.com (Google AI Studio)
LLM_API_KEY=...
```

> Defaults to Google Gemini (free). To use Groq instead, switch
> `PDFSIGN_LLM_BASE_URL` / `PDFSIGN_LLM_MODEL` (presets are in `.env.example`).
> Without a key the backend still runs, falling back to a keyword-based score
> and static email templates.
>
> Note: the **Gemini API key** (Google AI Studio) is separate from the
> **Gmail OAuth** credentials n8n needs (Google Cloud Console) — see
> `docs/n8n-integration.md`.

Then start the API:

```bash
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The UI runs at `http://localhost:5173`.

### n8n

- Import the workflow from:

```
n8n/agentic-internship-coordinator-workflow.json
```

- Configure:
  - Gmail OAuth credentials
  - ngrok URL
  - FastAPI endpoint — post applications to `POST /applications/from-n8n`

> If `PDFSIGN_API_SECRET_KEY` is set in `.env`, the n8n HTTP Request node must
> send `Authorization: Bearer <key>`. Leave it empty for open local testing.

---

## 💾 Data & Testing

- Processed applications are persisted to a SQLite file (`backend/applications.db`),
  so they survive restarts. The in-memory list has been removed.
- Run the backend test suite:

```bash
cd backend
pytest
```

---

## 📬 Example Flow

```
Candidate sends CV
        │
        ▼
Gmail Trigger
        │
        ▼
PDF Extraction
        │
        ▼
AI Analysis
        │
        ▼
Candidate Score
        │
        ▼
Interview / Reject
        │
        ▼
Automatic Email
```

---

## 👨‍💻 Authors

Computer Engineering Internship Project

AI-powered internship recruitment automation system.
