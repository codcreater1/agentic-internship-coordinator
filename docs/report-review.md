# End-of-internship report review

The other end of the system. Phase one decides whether a student may **start** a
placement and issues the agreement. This decides whether they **finished** one,
and issues the completion certificate the registrar acts on.

A student emails three PDFs. The service reads them, checks them against each
other, and either tells the student exactly what to correct or puts the package
in front of a coordinator to sign.

---

## What arrives

| Role | Document | Written by | Why it is needed |
|---|---|---|---|
| `report` | Internship Report | the student | What they say they did |
| `evaluation` | Employer Evaluation Form | workplace supervisor | The only independent voice in the package |
| `timesheet` | Attendance Record | host organisation | The countable claim: which days, how many hours |

**Filenames are never trusted.** Attachments are classified by reading them
([`report_extraction.py`](../backend/app/services/report_extraction.py)).
Renaming `report.pdf` to `attendance.pdf` changes nothing, and neither does the
order the mail client happens to present them in.

---

## Who decides

| | decides the outcome | can reject | can sign |
|---|---|---|---|
| Deterministic checks | ✅ everything | ✅ | ❌ |
| LLM | ❌ nothing | ❌ | ❌ |
| Named coordinator | final call | — | ✅ |

A completion certificate is an institutional claim about a real person — that
they attended twenty days at a named company. The evidence for it is countable:
dates, hours, a supervisor's signature, a score. Counting is what computers are
trustworthy at, so counting decides.

The model reads the report and raises questions for the coordinator. That is its
entire job, it runs *after* the status is already fixed, and the service decides
identically with it switched off.

### This phase does not degrade the way the application flow does

In [`application_service.py`](../backend/app/services/application_service.py) the
LLM *produces* the score, so an outage means no real evaluation happened, and an
application is held at `pending` rather than judged by the keyword fallback.

Here there is no such hazard. The verdict comes from counting dates and reading
signature fields, so a model outage costs the coordinator some commentary and
changes nothing about who gets a certificate. **A completion package is never
held because an API was down.**

---

## Statuses

The vocabulary is the one this project already uses, and the distinction matters
even more here than at application time.

| Status | Meaning | Signable |
|---|---|---|
| `request_clarification` | Something is missing or inconsistent and the student can fix it | ❌ |
| `pending` | Nothing is provably wrong, but a coordinator should look | ✅ with `acknowledge_warnings` |
| `approved` | Every check passed; waiting for a signature | ✅ |
| `rejected` | The two failures resending cannot fix | ❌ |
| `signed` | A named coordinator issued the certificate | — |

**Only two findings reject**: an employer score below the pass mark, and a
report copied from another accepted submission. Both need a conversation with
the coordinator, not a corrected attachment. Everything else asks the student to
fix one specific thing — the same principle the application flow follows for an
incomplete application, applied at the other end of the internship.

A rejection outranks a clarification, so a student whose employer failed them is
not also told to chase a missing stamp.

---

## The checks

Severity is the contract. A check that rejects where it should clarify refuses a
student for something they could have fixed, so the tests assert the severity,
not merely that something fired.

### Intake — [`report_service.py`](../backend/app/services/report_service.py)

Any of these **short-circuits** the pipeline; the content checks do not run.
Twenty findings over a package that is missing its evaluation form buries the
one thing the student needs to fix under nineteen that are downstream of it.

| Code | Severity | Fires when |
|---|---|---|
| `ATTACHMENT_COUNT` | clarify | Not exactly three attachments |
| `ATTACHMENT_EMPTY` | clarify | An attachment has zero bytes |
| `ATTACHMENT_NOT_PDF` | clarify | Magic-byte check failed — the extension is not consulted |
| `ATTACHMENT_UNREADABLE` | clarify | Corrupt, or password-protected |
| `ATTACHMENT_TOO_LONG` | clarify | Over 120 pages |
| `ATTACHMENT_NOT_TEXT` | clarify | Under 200 characters of text — a scan |
| `DOCUMENT_UNRECOGNISED` | clarify | Content matched no document type |
| `DOCUMENT_DUPLICATED` | clarify | Two attachments are the same role |
| `DOCUMENT_MISSING` | clarify | One of the three is absent |

Encrypted PDFs are refused rather than opened with an empty password: a document
we had to break into is not one we should attest to.

**The scan check matters more than it looks.** A photograph of a signed form
satisfies every text-based check *vacuously* — there is no text to contradict
anything, so nothing fires and the package looks clean. Reporting that as
verified would be worse than asking again. Vacuous passes are the dangerous
kind.

### Identity and placement — [`report_verification.py`](../backend/app/services/report_verification.py)

| Code | Severity | Fires when |
|---|---|---|
| `NAME_MISSING` / `NAME_MISMATCH` | clarify | A document states no student name, or the three disagree |
| `STUDENT_ID_MISSING` / `STUDENT_ID_MISMATCH` | clarify | No album number, or the three disagree |
| `COMPANY_MISSING` / `COMPANY_MISMATCH` | clarify | No host organisation, or the three disagree |
| `PERIOD_MISSING` / `PERIOD_INVALID` / `PERIOD_MISMATCH` | clarify | Dates unreadable, end before start, or the two documents disagree |

Names are compared after folding case, spacing and diacritics. Polish crossed L
and Turkish dotted/dotless I do not survive naive case folding, so they are
folded explicitly — a package must not be held because the company typed a name
in capitals. Album numbers keep their letter: `s24187` and `24187` are not the
same student.

### Attendance

A day counts when it is inside the declared period, marked present, carries at
least 4 hours, is not a duplicate, and is not a weekend.

| Code | Severity | Fires when |
|---|---|---|
| `ATTENDANCE_EMPTY` | clarify | No readable daily entries |
| `DAYS_SHORT` | clarify | Fewer than 20 verified days |
| `DUPLICATE_DATES` | clarify | A date appears twice — counted once regardless |
| `FUTURE_DATES` | clarify | Days claimed that have not happened |
| `DATES_OUTSIDE_PERIOD` | clarify | Days outside the declared window |
| `HOURS_IMPLAUSIBLE` | warning | Over 11 hours. Still counted |
| `HOURS_SHORT` | warning | Under 4 hours. Not counted |
| `WEEKEND_DAYS` | warning | Weekend entries listed. Not counted |
| `TOTAL_DAYS_MISMATCH` | warning | The stated total contradicts the document's own rows |
| `DECLARED_DAYS_MISMATCH` | warning | Report and attendance record state different totals |
| `ABSENT_DAYS` | info | Days marked absent |

Twenty weekdays plus the weekends between them is not twenty-six working days.
Weekend entries are excluded and reported, so "I padded the sheet" and "I
genuinely worked Saturdays" both land in front of a human.

A fourteen-hour day is a warning, not a refusal. It warrants asking the
supervisor, which is what a coordinator is for.

### Employer endorsement

| Code | Severity | Fires when |
|---|---|---|
| `EVAL_SCORE_MISSING` | clarify | No overall score |
| `EVAL_UNSIGNED` | clarify | Not marked signed |
| `EVAL_UNSTAMPED` | clarify | No company stamp |
| `SUPERVISOR_MISSING` | clarify | The form does not name who signed it |
| `EVAL_DATED_EARLY` | warning | Dated before the internship ended |
| **`EVAL_SCORE_LOW`** | **reject** | Below the pass mark of 60 |

An unparseable yes/no field reads as **No**. Every ambiguity resolves against
the submission.

### Report substance and originality

| Code | Severity | Fires when |
|---|---|---|
| `REPORT_SHORT` | clarify | Under 500 words |
| `SECTIONS_MISSING` | clarify | A required section heading is absent |
| `REPORT_SIMILARITY_ELEVATED` | warning | ≥ 0.60 cosine to an accepted report |
| **`REPORT_NOT_ORIGINAL`** | **reject** | ≥ 0.80 cosine to an accepted report |

Word count and section presence are weak proxies and are meant to be. They catch
the empty submission; they are not a grade.

The originality check exists because the realistic failure mode for internship
reports is not fabrication, it is circulation: last year's cohort passes its
reports down, or two students at the same company submit one document with the
names swapped. No per-document check catches this — each copy is individually
perfect. So each accepted report is kept as a TF-IDF vector and every new report
is scored against all of them
([`report_similarity.py`](../backend/app/services/report_similarity.py)). It is
plain Python: no dependency, no API cost, and it runs **before** the model is
called, so a copied report costs nothing to reject.

Three implementation notes:

- **Header lines are stripped before comparison.** `Student Name:` and friends
  are near-identical across every submission by construction; including them
  would inflate similarity between two entirely unrelated reports.
- **Only accepted reports join the corpus.** Indexing a rejected one would let a
  copy poison the index against the original it was taken from; indexing a
  clarification-held one would make the student's own corrected resubmission
  look plagiarised.
- **The corpus is rebuilt from SQLite at startup**
  ([`report_repository.accepted_report_bodies`](../backend/app/services/report_repository.py)).
  The index lives in memory, and without this a restart would amnesty a report
  copied from one accepted last week.

---

## Every clarification must be answerable

Every `clarify` and `reject` finding carries a `remedy`, and the student's email
is assembled from exactly those. A test enforces it — a request the student
cannot act on is treated as a bug, not a style problem.

```
2. Only 18 attended working days could be verified; 20 are required.
   What to do: Submit an attendance record showing at least 20 attended
   working days of at least 4 hours each, inside the declared internship
   period. If you did work those days, ask the company to reissue the record.
```

The LLM drafts a warmer version of the same message when it is available, with
the remedies passed in as data. A drafted email and a templated one ask for
exactly the same things.

---

## The certificate

Signed certificates carry the **SHA-256 of the three documents they attest to**,
printed on the face of the document.

A certificate detached from its documents attests to nothing — anyone holding it
could pair it with a different report. With the hash printed, the claim is
checkable: rehash the three files and compare. The hash is order-independent, so
attachment order cannot change it.

The certificate also states plainly what it does *not* claim:

> It attests to the completeness and internal consistency of the submitted
> record. It is not an assessment of the quality of the work performed.

If a coordinator signs a package that carried open points, the acknowledged
codes are printed on the certificate too. The document records the conditions
under which it was issued.

Rendering follows the UTA house style of
[`contract_service.py`](../backend/app/services/contract_service.py), with one
deliberate difference: it registers a TrueType font. Helvetica's WinAnsi
encoding has no glyphs for ł, ą, ę, ś, ż, ń or ğ, ş, ı, and this document prints
a real student's name. Transliteration is the fallback; plain Helvetica the last
resort.

> **Known gap:** `contract_service.py` has the same limitation and has not been
> given the same treatment. A student named Wiśniewska currently gets a correct
> completion certificate and a mangled internship agreement.

---

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/reports/` | Review a package: `intern_email` + three `files` |
| `POST` | `/reports/from-n8n` | Same, behind the shared bearer token |
| `GET` | `/reports/` | Coordinator queue. `?status=pending` to filter |
| `GET` | `/reports/by-id/{id}` | Full result, findings, advisory review |
| `GET` | `/reports/by-id/{id}/attachments/{role}` | Read back a submitted document |
| `POST` | `/reports/by-id/{id}/sign` | **The human gate.** Requires `coordinator_name` |
| `GET` | `/reports/by-id/{id}/certificate?token=` | Signed certificate, re-downloadable |
| `GET` | `/reports/for-application/{application_id}` | Every completion attempt for one candidate |
| `DELETE` | `/reports/by-id/{id}` | Remove a submission |

Addressing is by stable `id` under `/by-id/`, matching `/applications/`.

A held or rejected package returns **HTTP 201 with the status in the body**, not
a 4xx. It is a normal outcome, not a protocol error, and n8n should not have to
tell them apart.

`POST /sign` is the route with the interesting preconditions:

- a **rejected** package can never be signed;
- a package **held for clarification** can never be signed either — signing past
  a missing supervisor signature would produce a certificate resting on a
  document nobody signed;
- a **pending** package can be signed with `acknowledge_warnings: true`, and the
  acknowledged points are printed on the certificate;
- `coordinator_name` is required and rendered on the document.

---

## Linking to the application

A submission is matched to the candidate's application by email and stores
`application_id`, which is what lets the dashboard show one student's whole arc
from CV to certificate.

The match is best-effort. A student whose application predates this system, or
who applied from a different address, is still reviewed — the link is a
convenience, not a precondition.

Each submission is its own row, so a student asked to correct something and
resend produces a second row rather than overwriting the first.
`GET /reports/for-application/{id}` returns the whole history.

---

## Test documents

[`ata-test-docs/tool/completion_docs.py`](../ata-test-docs/tool/completion_docs.py)
generates the three attachments, including the failures — which are the point.

```bash
python ata-test-docs/tool/completion_docs.py --all --out completion
```

Nine scenarios, each perturbing exactly one thing so a firing gate is
diagnostic. The expected outcome for each lives in the `EXPECTED` dict in that
module, in the same spirit as `MANIFEST.csv` for the application corpus. All
data is synthetic.

```bash
cd backend && python -m pytest tests/test_reports.py -v
```
