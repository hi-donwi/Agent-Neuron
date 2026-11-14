"""A plain lexical baseline: Okapi BM25 over lowercase alphanumeric tokens."""

import math
import re
from collections import Counter
from collections.abc import Sequence

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class BM25:
    """BM25 with the usual defaults. Nothing is tuned to a dataset."""

    def __init__(self, documents: Sequence[str], k1: float = 1.5, b: float = 0.75) -> None:
        self._k1 = k1
        self._b = b
        self._counts = [Counter(tokenize(document)) for document in documents]
        self._lengths = [sum(counts.values()) for counts in self._counts]
        self._average = (sum(self._lengths) / len(self._lengths)) if self._lengths else 0.0
        frequency = Counter(term for counts in self._counts for term in counts)
        total = len(self._counts)
        self._idf = {
            term: math.log(1 + (total - seen + 0.5) / (seen + 0.5))
            for term, seen in frequency.items()
        }

    def scores(self, query: str) -> list[float]:
        """One score per document, in the order the documents were given."""
        terms = tokenize(query)
        result = []
        for counts, length in zip(self._counts, self._lengths, strict=True):
            norm = self._k1 * (1 - self._b + self._b * length / self._average) if length else 0.0
            score = 0.0
            for term in terms:
                seen = counts.get(term, 0)
                if seen:
                    score += self._idf[term] * seen * (self._k1 + 1) / (seen + norm)
            result.append(score)
        return result


# English function words. A query's remaining tokens are its content words.
STOPWORDS = frozenset(
    """
    a about after again all also an and any are as at be because been before being both but
    by can cannot could did do does each every for from had has have how i if in into is it
    its just may me more most must my no nor not now of off on once one only or other our
    out over own same should so some such than that the their them then there these they
    this those through to too under until up us very was we were what when where which
    while who whose why will with without would you your
    """.split()
)


def content_words(text: str) -> list[str]:
    return [token for token in tokenize(text) if token not in STOPWORDS]


def overlap_share(query: str, reference: str) -> float:
    """Share of the query's distinct content words that occur in the reference text."""
    words = set(content_words(query))
    if not words:
        return 0.0
    return len(words & set(tokenize(reference))) / len(words)
