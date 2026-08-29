# Changelog

All notable updates to the Agentic Internship Coordinator.

---

## [Unreleased]
### Fixed
- nginx served `index.html` with no cache directives, so browsers cached it
  heuristically and kept loading the previous deploy's hashed bundle — a new
  frontend release stayed invisible until a hard refresh. index.html is now
  `no-cache`; /assets/ (content-hashed) is immutable for a year.
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
