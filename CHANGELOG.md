# Changelog

All notable updates to the Agentic Internship Coordinator.

---

## [Unreleased]
### Added — end-of-internship report review
- New `/reports/*` API: a student emails three PDFs (internship report, employer
  evaluation form, attendance record) and the system verifies them against each
  other, then a named coordinator signs a completion certificate.
- Attachments are classified by reading them, not by filename or order.
- Deterministic checks decide the outcome; the LLM only reads the report and
  raises questions for the coordinator. Unlike CV screening, a model outage
  cannot hold a package — the verdict does not depend on it.
- Only a failing employer score or a copied report reject. Every other problem
  lands at `request_clarification` with a specific instruction, matching how the
  application flow already treats incomplete applications.
- Cross-submission originality check (TF-IDF, stdlib only) catches reports
  circulated between students, which no per-document check can see. Corpus is
  rebuilt from SQLite at startup.
- Certificates carry the SHA-256 of the three documents they attest to, so a
  certificate cannot be detached from what it certifies.
- `report_submissions` table, linked to an application by candidate email.
- `ata-test-docs/tool/completion_docs.py` generates the three documents across
  nine scenarios, failures included.
- 55 new tests; the suite is now 85.
### Added — completion queue in the dashboard
- Sidebar switches between the applications inbox and the new completion queue,
  with a badge counting only what is waiting on the coordinator.
- Queue tabs are organised by who acts next (to sign / with student / signed).
- Submission view shows verified figures, findings grouped by what they demand,
  the exact remedy the student was emailed, and the submitted PDFs with hashes.
- Certificate panel signs from a drawn signature; it does not appear for a
  rejected or clarification-held package, and requires an explicit
  acknowledgement for one carrying open points.
### Changed
- `StorageService.task_dir()` added — the report flow stores several files per
  task, where the contract flow stores exactly two and reaches them by name.
## 2026-07-07
- Daily sync: AI evaluation service operational, n8n workflow active, SQLite stable
## 2026-07-06
- Daily sync: AI evaluation service operational, n8n workflow active, SQLite stable
## 2026-07-05
- Daily sync: AI evaluation service operational, n8n workflow active, SQLite stable

## 2026-07-04
- Daily service check: AI evaluation engine operational (Groq llama-3.3-70b)
- Backend health: https://pomelo-6.codewithpeter.com/health — OK
- Frontend: https://pomelo-7.codewithpeter.com — serving
- n8n workflow: active, Gmail trigger polling
- SQLite persistence: stable
