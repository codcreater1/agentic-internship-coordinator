# System Architecture

## Main Components

### Frontend

* Candidate application form
* Status tracking page

### Backend (FastAPI)

* Application management
* File handling
* Agent orchestration

### LangGraph

* Coordinator Agent
* CV Screening Agent
* Matching Agent
* Report Agent

### n8n

* Workflow automation
* Email triggers
* Notifications

### Gmail

* Interview invitations
* Acceptance emails
* Rejection emails

## Workflow

Candidate
↓
Frontend
↓
FastAPI
↓
LangGraph Agents
↓
n8n
↓
Gmail
