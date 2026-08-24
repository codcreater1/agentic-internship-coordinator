"""Detect reports copied from other reports.

The realistic failure mode for internship reports is not fabrication, it is
circulation: last year cohort passes its reports down, or two interns at the
same company submit one document with the names swapped. Neither is caught by
any per-document check, because each copy is individually perfect.

So originality is measured *between* submissions. Each accepted report is kept
as a TF-IDF vector; each new report is scored against all of them by cosine
similarity. Above ``SIMILARITY_REJECT_THRESHOLD`` the package is rejected;
between the warn and reject thresholds a human is asked to look.

Implemented in plain Python on purpose. It is roughly forty lines of counting,
it runs in milliseconds against a realistic corpus, it costs nothing per check,
and it adds no dependency to a service that already carries enough. It also
runs *before* any model is called, so a copied report never reaches a paid API.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field

_TOKEN_RE = re.compile(r"[a-zçğıöşü]+", re.IGNORECASE)

# Words too common to carry a signal. Kept deliberately short: an aggressive
# stop list would strip the domain vocabulary that makes two reports about the
# same work look alike, which is precisely what we want to detect.
_STOPWORDS = frozenset(
    """
    a an and are as at be been by for from has have i in is it its of on or
    that the this to was were will with we our my
    ve ile bir bu da de icin olarak ben
    """.split()
)


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens, stopwords and one-character words removed."""
    return [
        token
        for token in (match.group(0).lower() for match in _TOKEN_RE.finditer(text))
        if len(token) > 1 and token not in _STOPWORDS
    ]


@dataclass
class _Document:
    doc_id: str
    counts: Counter
    length: int


@dataclass
class SimilarityIndex:
    """An in-memory corpus of accepted reports.

    Not persistent, matching the rest of this codebase, which keeps its
    submissions in module-level lists. A real deployment would back this with
    the same store as the submissions themselves; the interface would not
    change, only :meth:`add` and :meth:`_documents` would.
    """

    _docs: list[_Document] = field(default_factory=list)

    # -- corpus ---------------------------------------------------------

    def add(self, doc_id: str, text: str) -> None:
        """Add an accepted report to the corpus it will be compared against."""
        counts = Counter(tokenize(text))
        if not counts:
            return
        self._docs.append(_Document(doc_id=doc_id, counts=counts, length=sum(counts.values())))

    def __len__(self) -> int:
        return len(self._docs)

    # -- query ----------------------------------------------------------

    def most_similar(self, text: str) -> tuple[float, str | None]:
        """Return ``(score, doc_id)`` for the closest document in the corpus.

        Returns ``(0.0, None)`` for an empty corpus - the first submission of a
        term has nothing to be similar to, and must not be penalised for it.
        """
        if not self._docs:
            return 0.0, None

        query_counts = Counter(tokenize(text))
        if not query_counts:
            return 0.0, None

        idf = self._idf(extra=query_counts)
        query_vec = self._vector(query_counts, sum(query_counts.values()), idf)

        best_score = 0.0
        best_id: str | None = None

        for doc in self._docs:
            score = _cosine(query_vec, self._vector(doc.counts, doc.length, idf))
            if score > best_score:
                best_score, best_id = score, doc.doc_id

        return best_score, best_id

    # -- internals ------------------------------------------------------

    def _idf(self, extra: Counter | None = None) -> dict[str, float]:
        """Inverse document frequency over the corpus plus the query.

        The query is folded into the document count so that a term appearing
        only in the query still receives a finite weight rather than dividing
        by zero.
        """
        n_docs = len(self._docs) + (1 if extra else 0)
        doc_freq: Counter = Counter()

        for doc in self._docs:
            doc_freq.update(doc.counts.keys())
        if extra:
            doc_freq.update(extra.keys())

        # Smoothed IDF - never zero, so a term shared by every document still
        # contributes a little rather than vanishing.
        return {
            term: math.log((n_docs + 1) / (freq + 1)) + 1.0
            for term, freq in doc_freq.items()
        }

    @staticmethod
    def _vector(counts: Counter, length: int, idf: dict[str, float]) -> dict[str, float]:
        """L2-normalised TF-IDF vector for one document."""
        if length == 0:
            return {}

        raw = {
            term: (count / length) * idf.get(term, 1.0)
            for term, count in counts.items()
        }
        norm = math.sqrt(sum(value * value for value in raw.values()))
        if norm == 0:
            return {}
        return {term: value / norm for term, value in raw.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    """Cosine similarity of two L2-normalised sparse vectors."""
    if not a or not b:
        return 0.0
    # Iterate the smaller vector; the dot product is symmetric.
    if len(b) < len(a):
        a, b = b, a
    return sum(value * b.get(term, 0.0) for term, value in a.items())


# Module-level singleton, mirroring the other services in this package.
similarity_index = SimilarityIndex()
