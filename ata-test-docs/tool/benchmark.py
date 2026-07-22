"""Score a running backend against the generated test corpus.

Sends documents to POST /cv/analyze and compares the returned status with the
outcome MANIFEST.csv expects for that document's category.

    python tool/benchmark.py                    # 2 docs per category
    python tool/benchmark.py --per-category 5
    python tool/benchmark.py --api http://127.0.0.1:8000
    python tool/benchmark.py --files 073_ok_sanne-jansen.pdf 022_handwritten_*.pdf

Run `python tool/generate.py` first — the corpus is not committed.

⚠️ Token budget: each document costs roughly 2k LLM tokens. Groq's free tier
allows 100k tokens per DAY, so a full 100-document sweep is not possible and
even ~40 documents exhausts it. Keep --per-category small.

A score that is a multiple of 8 with no strengths is the keyword fallback,
which means the LLM call failed (usually the quota) — the run is then
measuring nothing and is reported as SKIPPED rather than counted.
"""

from __future__ import annotations

import argparse
import csv
import fnmatch
import json
import pathlib
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "documents"
MANIFEST = ROOT / "MANIFEST.csv"

# The statuses this system may legitimately return for each corpus category.
ACCEPTABLE: dict[str, set[str]] = {
    "ok": {"interview"},
    "handwritten": {"interview"},
    # Injections must not raise the score; merit alone decides.
    "malicious": {"interview", "pending"},
    "rejected": {"rejected"},
    "missing_info": {"request_clarification"},
    "clarification": {"request_clarification"},
    # An unreadable scan may be refused outright or queried — never approved.
    "broken": {"request_clarification", "rejected", "pending"},
}

CATEGORY_ORDER = [
    "ok", "handwritten", "malicious", "rejected",
    "missing_info", "clarification", "broken",
]


def analyse(api: str, pdf: pathlib.Path) -> dict:
    boundary = "----atabench"
    parts = []
    for key, value in (("name", "Benchmark"), ("email", "benchmark@example.com")):
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; "
            f'name="{key}"\r\n\r\n{value}\r\n'.encode()
        )
    parts.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
        f'filename="{pdf.name}"\r\nContent-Type: application/pdf\r\n\r\n'.encode()
        + pdf.read_bytes()
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())

    request = urllib.request.Request(
        f"{api}/cv/analyze",
        data=b"".join(parts),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=240) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return {"status": f"HTTP_{exc.code}", "candidate_score": -1}
    except Exception as exc:  # noqa: BLE001 — a failed probe is a result too
        return {"status": f"ERROR_{type(exc).__name__}", "candidate_score": -1}


def looks_like_fallback(result: dict) -> bool:
    """Keyword-fallback scores are multiples of 8 and carry no strengths."""
    score = result.get("candidate_score", -1)
    return score >= 0 and score % 8 == 0 and not result.get("report", "").strip().startswith("AI")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--per-category", type=int, default=2)
    parser.add_argument("--files", nargs="*", help="glob(s) — overrides --per-category")
    args = parser.parse_args()

    if not MANIFEST.is_file():
        print("MANIFEST.csv not found — run: python tool/generate.py", file=sys.stderr)
        return 2

    rows = list(csv.DictReader(MANIFEST.open(encoding="utf-8")))

    if args.files:
        selected = [r for r in rows if any(fnmatch.fnmatch(r["file"], p) for p in args.files)]
    else:
        by_category: dict[str, list[dict]] = {}
        for row in rows:
            by_category.setdefault(row["category"], []).append(row)
        selected = [
            row
            for category in CATEGORY_ORDER
            for row in by_category.get(category, [])[: args.per_category]
        ]

    print(f"{len(selected)} documents · ~{len(selected) * 2}k tokens\n")
    print(f"{'category':<14} {'file':<42} {'status':<22} {'score':>5}  verdict")
    print("-" * 98)

    passed = failed = skipped = 0
    failures: list[str] = []

    for row in selected:
        pdf = DOCS / row["file"]
        if not pdf.is_file():
            print(f"{row['category']:<14} {row['file'][:41]:<42} {'MISSING FILE':<22}")
            continue

        result = analyse(args.api, pdf)
        status = result.get("status", "?")
        score = result.get("candidate_score", -1)

        if looks_like_fallback(result):
            verdict, skipped = "SKIP (LLM down)", skipped + 1
        elif status in ACCEPTABLE.get(row["category"], set()):
            verdict, passed = "PASS", passed + 1
        else:
            verdict, failed = "FAIL", failed + 1
            failures.append(f"{row['file']}: got {status}, expected one of "
                            f"{sorted(ACCEPTABLE[row['category']])}")

        print(f"{row['category']:<14} {row['file'][:41]:<42} {status:<22} {score:>5}  {verdict}")

    print("-" * 98)
    counted = passed + failed
    rate = f"{100 * passed // counted}%" if counted else "n/a"
    print(f"{passed}/{counted} correct ({rate})"
          + (f" · {skipped} skipped — LLM unavailable, quota likely spent" if skipped else ""))

    if failures:
        print("\nFailures:")
        for line in failures:
            print(f"  - {line}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
