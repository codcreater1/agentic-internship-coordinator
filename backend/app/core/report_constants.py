"""Thresholds and vocabulary for the end-of-internship report review.

Phase 1 of this system decides whether someone may *start* an internship.
This is the other end: the student has finished, and emails three documents
proving it. The output is a completion certificate the university acts on.

The statuses are deliberately the ones this project already uses, because the
distinction they encode matters even more here than at application time:

``request_clarification``
    Something is missing or inconsistent, and the student can fix it. An
    unsigned evaluation form, nineteen days instead of twenty, a name that
    does not match across the three documents. Nobody is refused for an
    omission they can correct — the same principle the application flow
    follows (see :mod:`app.services.application_service`).

``pending``
    Nothing is provably wrong, but a human should look: weekend days padding
    the count, implausible hours, a report unusually similar to another. Also
    where a submission lands when the model is unreachable.

``approved``
    Every gate passed. Waiting for a coordinator to sign — passing the gates
    is necessary for a certificate, never sufficient.

``rejected``
    Reserved for the two failures resending cannot fix: an employer score
    below the pass mark, and a report copied from another accepted submission.
    Both need a conversation with the coordinator, not a corrected attachment.

``signed``
    A named coordinator issued the certificate.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# Attendance
# --------------------------------------------------------------------------- #

MIN_WORKING_DAYS = 20
MIN_DAILY_HOURS = 4.0

# Above this a day is flagged for a human rather than refused. A fourteen-hour
# day is worth asking the supervisor about; it is not grounds for automatically
# refusing a student's whole internship.
MAX_DAILY_HOURS = 11.0

COUNT_WEEKEND_DAYS = False

# --------------------------------------------------------------------------- #
# Report substance
# --------------------------------------------------------------------------- #

MIN_REPORT_WORDS = 500

REQUIRED_REPORT_SECTIONS = (
    "introduction",
    "company",
    "work performed",
    "technologies",
    "conclusion",
)

# --------------------------------------------------------------------------- #
# Employer evaluation
# --------------------------------------------------------------------------- #

MIN_EVALUATION_SCORE = 60

# --------------------------------------------------------------------------- #
# Originality
# --------------------------------------------------------------------------- #

# TF-IDF cosine against previously accepted reports. Above the reject line the
# package is refused; between the two a human decides, because two interns on
# the same team writing about the same project legitimately look alike.
SIMILARITY_REJECT_THRESHOLD = 0.80
SIMILARITY_WARN_THRESHOLD = 0.60

# --------------------------------------------------------------------------- #
# Document handling
# --------------------------------------------------------------------------- #

REQUIRED_ATTACHMENT_COUNT = 3

MAX_DOCUMENT_PAGES = 120

# A PDF yielding less text than this is a scan. It is held for clarification
# rather than passed: a photograph of a form satisfies every text-based check
# vacuously, and reporting that as verified would be worse than asking again.
MIN_EXTRACTABLE_CHARS = 200

# --------------------------------------------------------------------------- #
# Statuses
# --------------------------------------------------------------------------- #

STATUS_APPROVED = "approved"
STATUS_CLARIFICATION = "request_clarification"
STATUS_PENDING = "pending"
STATUS_REJECTED = "rejected"
STATUS_SIGNED = "signed"

# Statuses a coordinator may sign. A package held for clarification or rejected
# must change state by being resubmitted or discussed, never by being signed.
SIGNABLE_STATUSES = (STATUS_APPROVED, STATUS_PENDING)
