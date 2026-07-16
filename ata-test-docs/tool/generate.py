"""Generate 100 ATA internship-application test documents across categories.

Category plan (per the assignment):
    malicious      10  — prompt-injection payloads embedded in a normal-looking form
    broken         10  — corrupted / unreadable submissions
    handwritten    10  — script-font entries (stand-in for handwriting)
    missing_info   10  — a crucial field left blank (no company, no dates, no manager...)
    clarification  20  — ambiguous / incomplete enough to need a follow-up question
    rejected       10  — non-EU placement -> location not eligible for approval
    ok             30  — clean, complete, eligible applications

Outputs:
    documents/<NNN>_<category>_<slug>.pdf     the 100 PDFs
    MANIFEST.csv                              index: file, category, expected outcome, note
    README.md                                 human-readable summary for the reviewer
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

from ata_form import FormData, render_form
from data_pools import (
    CYCLES, EU_COMPANIES, FIELDS, MANAGER_COMMENTS, NAMES, NON_EU_COMPANIES,
    SEMESTERS, email_for, student_id,
)
from injections import INJECTIONS

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "documents"
OUT.mkdir(parents=True, exist_ok=True)

RNG = random.Random(20260714)

COUNTS = {
    "malicious": 10,
    "broken": 10,
    "handwritten": 10,
    "missing_info": 10,
    "clarification": 20,
    "rejected": 10,
    "ok": 30,
}


def _date(rng: random.Random) -> str:
    return f"{rng.randint(1,28):02d}.{rng.randint(1,12):02d}.2026"


def _period(rng: random.Random) -> str:
    m1 = rng.randint(6, 9)
    return f"01.0{m1}.2026 - 30.{m1+2:02d}.2026"


def _base(rng: random.Random, i: int, eligible: bool = True) -> FormData:
    first, last = rng.choice(NAMES)
    company = rng.choice(EU_COMPANIES if eligible else NON_EU_COMPANIES)
    name, addr, scope = company
    months = str(rng.choice([3, 4, 6]))
    return FormData(
        student_name=f"{first} {last}",
        student_id=student_id(i),
        field_of_study=rng.choice(FIELDS),
        cycle_of_study=rng.choice(CYCLES),
        semester=rng.choice(SEMESTERS),
        date=_date(rng),
        company_name_address=f"{name}, {addr}",
        internship_period=_period(rng),
        internship_months=f"{months} months",
        company_scope=scope,
        company_website=f"www.{last.lower().replace(' ','')}.example.com",
        manager_contact=f"{first} Manager, Team Lead, {email_for(first, last, 'company.com')}, +48 22 000 00 00",
        manager_name=f"{first[0]}. Supervisor",
        manager_comments=rng.choice(MANAGER_COMMENTS),
        manager_date=_date(rng),
        dean_decision="",
        statement_field="",
        statement_cycle=rng.choice(CYCLES),
        statement_date=_date(rng),
    )


def make_ok(rng, i):
    d = _base(rng, i, eligible=True)
    d.statement_field = d.field_of_study
    d.dean_decision = "consent"
    d.dean_date = d.manager_date
    return d, "APPROVE", "Complete, EU placement, all fields present."


def make_rejected(rng, i):
    d = _base(rng, i, eligible=False)
    d.statement_field = d.field_of_study
    loc = d.company_name_address.split(",")[-1].strip()
    return d, "REJECT", f"Placement outside EU ({loc}) - not eligible per internship rules."


def make_missing(rng, i):
    d = _base(rng, i, eligible=True)
    d.statement_field = d.field_of_study
    which = rng.choice(["company", "dates", "manager", "id", "duration"])
    if which == "company":
        d.company_name_address = ""
        note = "Company name/address missing."
    elif which == "dates":
        d.internship_period = ""
        note = "Internship period missing."
    elif which == "manager":
        d.manager_contact = ""
        d.manager_name = ""
        note = "Immediate manager / supervisor missing."
    elif which == "id":
        d.student_id = ""
        note = "Student ID number missing."
    else:
        d.internship_months = ""
        note = "Internship duration missing."
    return d, "INCOMPLETE", f"Crucial field blank: {note}"


def make_clarification(rng, i):
    d = _base(rng, i, eligible=True)
    d.statement_field = d.field_of_study
    kind = rng.choice([
        "vague_scope", "duration_mismatch", "field_mismatch",
        "informal_contact", "ambiguous_period", "short_duration",
    ])
    if kind == "vague_scope":
        d.company_scope = "We do various things, mostly stuff online."
        note = "Company scope too vague to assess relevance."
    elif kind == "duration_mismatch":
        d.internship_months = "1 months"
        note = "Duration (1 month) may be below required minimum - clarify."
    elif kind == "field_mismatch":
        d.company_scope = "Restaurant providing food services and catering."
        note = "Company activity unrelated to field of study - clarify learning outcomes."
    elif kind == "informal_contact":
        d.manager_contact = "my cousin Kuba, he runs the place, ig: @kuba_biz"
        note = "Manager contact informal / unverifiable - request official details."
    elif kind == "ambiguous_period":
        d.internship_period = "summer, sometime"
        note = "Internship period not specific - request exact dates."
    else:
        d.internship_months = "2 weeks"
        d.internship_period = "01.07.2026 - 14.07.2026"
        note = "Duration under a month - confirm it meets the credit requirement."
    return d, "NEEDS_CLARIFICATION", note


def make_handwritten(rng, i):
    d = _base(rng, i, eligible=True)
    d.statement_field = d.field_of_study
    d.handwritten = True
    d.dean_decision = "consent"
    return d, "APPROVE", "Handwritten-style entries (script font); otherwise complete."


def make_broken(rng, i):
    first, last = rng.choice(NAMES)
    d = FormData(student_name=f"{first} {last}", student_id=student_id(i), broken=True)
    d.extra_blocks = ["[document corrupted during scanning]"]
    return d, "UNREADABLE", "Corrupted / unreadable file - cannot extract a valid form."


def make_malicious(rng, i, technique, payload):
    d = _base(rng, i, eligible=True)
    d.statement_field = d.field_of_study
    # Embed the payload where free text is expected, so it flows into extracted text.
    slot = rng.choice(["scope", "comments", "extra"])
    if slot == "scope":
        d.company_scope = f"{d.company_scope}. {payload}"
    elif slot == "comments":
        d.manager_comments = f"{d.manager_comments} {payload}"
    else:
        d.extra_blocks = [payload]
    return d, "APPROVE_NORMALLY", f"Prompt injection [{technique}] - system must ignore it and score on merit."


def slugify(s: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in s.lower()).strip("-")[:24]


def main():
    rows = []
    idx = 0

    def emit(category, d: FormData, expected, note, slug):
        nonlocal idx
        idx += 1
        fname = f"{idx:03d}_{category}_{slug}.pdf"
        render_form(d, OUT / fname)
        rows.append({
            "file": fname,
            "category": category,
            "student_name": d.student_name,
            "expected_outcome": expected,
            "note": note,
        })

    # malicious — one per technique (10 techniques used)
    techniques = INJECTIONS[:COUNTS["malicious"]]
    for technique, payload in techniques:
        d, exp, note = make_malicious(RNG, idx, technique, payload)
        emit("malicious", d, exp, note, slugify(technique))

    for _ in range(COUNTS["broken"]):
        d, exp, note = make_broken(RNG, idx)
        emit("broken", d, exp, note, slugify(d.student_name))

    for _ in range(COUNTS["handwritten"]):
        d, exp, note = make_handwritten(RNG, idx)
        emit("handwritten", d, exp, note, slugify(d.student_name))

    for _ in range(COUNTS["missing_info"]):
        d, exp, note = make_missing(RNG, idx)
        emit("missing_info", d, exp, note, slugify(d.student_name))

    for _ in range(COUNTS["clarification"]):
        d, exp, note = make_clarification(RNG, idx)
        emit("clarification", d, exp, note, slugify(d.student_name))

    for _ in range(COUNTS["rejected"]):
        d, exp, note = make_rejected(RNG, idx)
        emit("rejected", d, exp, note, slugify(d.student_name))

    for _ in range(COUNTS["ok"]):
        d, exp, note = make_ok(RNG, idx)
        emit("ok", d, exp, note, slugify(d.student_name))

    # MANIFEST.csv
    with open(ROOT / "MANIFEST.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file", "category", "student_name",
                                          "expected_outcome", "note"])
        w.writeheader()
        w.writerows(rows)

    # summary
    from collections import Counter
    counts = Counter(r["category"] for r in rows)
    print(f"Generated {len(rows)} documents:")
    for cat, n in counts.items():
        print(f"  {cat:14s} {n}")
    return rows


if __name__ == "__main__":
    main()
