# n8n Integration Plan

## Goal

Create an automated email-based internship application workflow.

## Final Flow

Candidate Email
↓
Gmail Trigger
↓
Extract Candidate Information
↓
HTTP Request to Backend
↓
FastAPI Backend
↓
CV Analysis Agent
↓
Matching Agent
↓
Report Agent
↓
Backend Response
↓
Gmail Send Email

## Backend Endpoint

POST /applications/

## Request Example

```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "cv_text": "Python, FastAPI, SQL..."
}
```

## Response Example

```json
{
  "candidate_score": 85,
  "recommended_role": "Backend Developer Internship",
  "status": "interview",
  "report": "Candidate evaluation report",
  "email_subject": "Interview Invitation",
  "email_body": "Dear Candidate..."
}
```

## Required n8n Nodes

1. Gmail Trigger
2. Set Node
3. HTTP Request Node
4. Gmail Send Email Node

## Status Handling

interview → send interview invitation

pending → send under review email

rejected → send rejection email