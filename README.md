<div align="center">

# 🤖 Agentic Internship Coordinator

**An AI-powered internship-application screening system** — it reads a candidate's CV, evaluates it with an LLM agent workflow, decides interview / pending / reject, drafts a personalised email, and generates an official university internship agreement for the coordinator to sign.

Built for real use at the university (UTA – Akademia Techniczno-Artystyczna w Warszawie).

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?logo=langchain&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=black)
![LangFuse](https://img.shields.io/badge/Observability-LangFuse-6366F1)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

</div>

---

## ✨ What it does

A candidate emails their CV → the system evaluates it end-to-end and replies automatically, while a recruiter dashboard gives full visibility and a one-click signing flow.

- 📄 **PDF CV ingestion** — via email (n8n Gmail trigger) or direct API/dashboard upload
- 🧠 **LLM agent evaluation** — LangGraph workflow scores 0–100, extracts strengths/weaknesses, recommends the best-fit internship role
- ✉️ **Personalised emails** — AI-drafted interview / under-review / rejection messages (with safe static-template fallback)
- 📝 **Official contract generation** — produces the UTA *Appendix No. 3* internship agreement, signed electronically in the dashboard (canvas signature pad → embedded in the PDF)
- 📊 **Recruiter dashboard** — React UI with live candidate inbox, evaluation detail, and contract signing
- 🔭 **LLM observability** — every model call traced in LangFuse (latency, tokens, prompt, output)
- 🛡️ **Prompt-injection hardened** — evaluated against a 10-technique red-team set (see [Security](#️-security--robustness))
- 💾 **Persistent** — applications stored in SQLite, survive restarts

---

## 🌐 Live demo

| Service | URL |
|---|---|
| Dashboard (frontend) | https://pomelo-7.codewithpeter.com |
| API (backend) | https://pomelo-6.codewithpeter.com |
| Health check | https://pomelo-6.codewithpeter.com/health |

> Deployed on Coolify (Docker) behind a Caddy reverse proxy.

---

## 🏗️ Architecture

```mermaid
flowchart TD
    A[Candidate emails CV PDF] --> B[n8n Gmail Trigger]
    B --> C[Extract PDF text]
    C --> D[FastAPI backend]
    D --> E[LangGraph agent workflow]
    E --> F[LLM evaluation - Groq llama-3.3-70b]
    F --> G[Score + role + strengths/weaknesses]
    G --> H{Decision}
    H -->|>= 70| I[Interview + generate UTA contract]
    H -->|50-69| J[Pending / under review]
    H -->|< 50| K[Rejected]
    I --> L[AI-drafted email reply]
    J --> L
    K --> L
    D --> M[(SQLite store)]
    M --> N[React dashboard]
    N --> O[Coordinator signs contract]
    F -.trace.-> P[LangFuse observability]
```

Direct API / dashboard uploads follow the same path from **FastAPI backend** onward, bypassing the email trigger.

---

## 🛠️ Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, Uvicorn |
| AI workflow | LangGraph, OpenAI-compatible SDK |
| LLM | Groq `llama-3.3-70b-versatile` (default) — any OpenAI-compatible endpoint (Gemini, OpenAI…) |
| Observability | LangFuse |
| Frontend | React + Vite |
| Automation | n8n (Gmail trigger + reply) |
| PDF | PyMuPDF, reportlab, pypdf |
| Storage | SQLite (stdlib) |
| Deployment | Docker, Coolify, Caddy |

---

## 🔌 API reference

Base URL: `/` (no global prefix). Interactive docs at `/docs`.

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Service + AI status |
| `POST` | `/cv/analyze` | Evaluate an uploaded PDF CV (multipart: `name`, `email`, `file`) |
| `POST` | `/cv/analyze-text` | Evaluate raw CV text (JSON) |
| `GET` | `/applications/` | List all applications (newest first) |
| `POST` | `/applications/` | Create + evaluate an application |
| `POST` | `/applications/from-n8n` | Ingest from n8n (optional Bearer auth) |
| `DELETE` | `/applications/by-id/{id}` | Delete an application |
| `GET` | `/applications/{index}/contract-preview` | Inline PDF preview of the contract |
| `POST` | `/applications/{index}/sign` | Embed the coordinator's signature |
| `GET` | `/pdf/download/{task_id}` | Download a signed contract (token-gated) |

---

## 🛡️ Security & robustness

Because the evaluator is an LLM reading untrusted candidate documents, the pipeline was **red-teamed against prompt injection** using a 10-technique test set (direct override, role hijack, system-prompt leak, output-format hijack, authority spoofing, context termination, payload splitting, encoded instructions, reverse psychology, tool abuse).

| | Before hardening | After hardening |
|---|---|---|
| Injections that manipulated the score | **7 / 10** | **0 / 10** |
| Clean-document scores | baseline | unchanged |

**Mitigations:** untrusted CV text is delimited (`<APPLICANT_DOCUMENT>`) and the model is instructed to treat it as data only, never as instructions, and to flag manipulation attempts as a weakness. Additional layers: optional Bearer-token auth on the n8n ingest endpoint, HMAC-signed download tokens, and signature-image normalisation (strips metadata, defangs polyglots).

The 100-document test corpus used for this evaluation is generated by the tooling under `ata-test-docs/` (7 categories, each with an expected-outcome manifest).

---

## ⚙️ Getting started (local)

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env      # then edit .env
uvicorn app.main:app --reload
```

Set a **free** LLM key in `.env` to enable AI evaluation (falls back to a keyword score without one):

```bash
LLM_API_KEY=gsk_...                                   # Groq (free) — get one at console.groq.com
PDFSIGN_LLM_BASE_URL=https://api.groq.com/openai/v1
PDFSIGN_LLM_MODEL=llama-3.3-70b-versatile
```

Optional — enable LangFuse tracing:

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

### Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

Point the UI at the API with `VITE_API_URL` (defaults to `http://localhost:8000`).

### n8n

Import `n8n/agentic-internship-coordinator-workflow.json`, then configure the Gmail OAuth credentials and set the HTTP node to `POST {backend}/applications/from-n8n`. See `docs/n8n-integration.md`.

---

## 🐳 Deployment (Docker / Coolify)

A root `Dockerfile` builds the backend; `docker-compose.yaml` runs backend + frontend. On Coolify: Build Pack = Dockerfile, Base Directory = `/`, and mount a `/data` volume for the SQLite DB and generated contracts. Environment variables use the `PDFSIGN_` prefix (except `LLM_API_KEY` and the `LANGFUSE_*` keys).

---

## 🧪 Testing

```bash
cd backend
pytest                 # hermetic, offline unit tests
```

Plus the 100-document prompt-injection / category corpus under `ata-test-docs/` for end-to-end evaluation.

---

## 📂 Project structure

```
backend/     FastAPI app — routers, agents (LangGraph), services, core (llm, config, security)
frontend/    React + Vite dashboard
n8n/         Gmail → evaluate → reply workflow
docs/        Integration guides
Dockerfile   Root image (backend); docker-compose for full stack
```

---

## 📜 License

MIT — see [LICENSE](LICENSE).

<div align="center">
Computer Engineering internship project · AI-powered recruitment automation
</div>
