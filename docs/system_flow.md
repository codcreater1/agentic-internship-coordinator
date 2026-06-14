# System Workflow

```text
Candidate Email
        ↓
Gmail
        ↓
n8n Trigger
        ↓
FastAPI Backend
        ↓
CV Analysis Agent
        ↓
Matching Agent
        ↓
Report Agent
        ↓
JSON Result
        ↓
n8n
        ↓
Gmail Response
```

## Description

1. Candidate sends internship application via email.
2. Gmail receives the application.
3. n8n triggers the workflow.
4. Backend analyzes the CV.
5. LangGraph agents evaluate the candidate.
6. A score and recommendation are generated.
7. n8n sends the final response email.