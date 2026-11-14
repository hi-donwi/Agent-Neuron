"""Evaluation metrics for classifiers that may abstain. Standard library only."""

import math
from collections.abc import Sequence


def wilson_interval(successes: int, total: int, z: float = 1.959964) -> tuple[float, float]:
    """Wilson score interval for a proportion; z defaults to the 95% level."""
    if total <= 0:
        raise ValueError("an interval needs at least one observation")
    proportion = successes / total
    denominator = 1 + z * z / total
    centre = (proportion + z * z / (2 * total)) / denominator
    half = z * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total))
    half /= denominator
    low = 0.0 if successes == 0 else max(0.0, centre - half)
    high = 1.0 if successes == total else min(1.0, centre + half)
    return low, high


def auroc(positives: Sequence[float], negatives: Sequence[float]) -> float:
    """Chance that a random positive outscores a random negative; a tie counts half."""
    if not positives or not negatives:
        raise ValueError("both sides need at least one score")
    wins = 0.0
    for positive in positives:
        for negative in negatives:
            if positive > negative:
                wins += 1.0
            elif positive == negative:
                wins += 0.5
    return wins / (len(positives) * len(negatives))


def expected_calibration_error(
    confidences: Sequence[float], correct: Sequence[bool], bins: int = 10
) -> float:
    """Share-weighted gap between confidence and accuracy over equal-width bins."""
    if len(confidences) != len(correct) or not confidences:
        raise ValueError("confidences and outcomes must be the same non-zero length")
    totals = [0] * bins
    hits = [0] * bins
    confidence_sums = [0.0] * bins
    for confidence, outcome in zip(confidences, correct, strict=True):
        index = min(int(confidence * bins), bins - 1)
        totals[index] += 1
        hits[index] += bool(outcome)
        confidence_sums[index] += confidence
    error = 0.0
    for total, hit, confidence_sum in zip(totals, hits, confidence_sums, strict=True):
        if total:
            error += abs(hit / total - confidence_sum / total) * total / len(confidences)
    return error


def percentile(values: Sequence[float], q: int) -> float:
    """Nearest-rank percentile: the smallest value with at least q percent at or below it."""
    if not values:
        raise ValueError("a percentile needs at least one value")
    ordered = sorted(values)
    rank = max(1, math.ceil(q * len(ordered) / 100))
    return ordered[rank - 1]


def threshold_for_false_accept(scores: Sequence[float], max_rate: float) -> float:
    """Threshold t such that at most max_rate of these scores are strictly above t.

    The scores are confidences on inputs that should be refused. A router that accepts
    only when its confidence is above t then accepts at most that share of them. Ties
    are resolved against acceptance.
    """
    if not scores:
        raise ValueError("a threshold needs at least one score")
    allowed = math.floor(max_rate * len(scores) + 1e-9)
    ordered = sorted(scores, reverse=True)
    if allowed >= len(ordered):
        return -math.inf
    return ordered[allowed]


def paired_sign_test(first: Sequence[bool], second: Sequence[bool]) -> tuple[int, int, float]:
    """Compare two classifiers on the same cases: an exact two-sided sign test.

    Returns how many cases only the first got right, how many only the second got right,
    and the chance of a split at least this uneven if neither were better. Cases both got
    right or both got wrong carry no information and are ignored.
    """
    if len(first) != len(second):
        raise ValueError("both classifiers must be scored on the same cases")
    only_first = sum(a and not b for a, b in zip(first, second, strict=True))
    only_second = sum(b and not a for a, b in zip(first, second, strict=True))
    discordant = only_first + only_second
    if discordant == 0:
        return 0, 0, 1.0
    tail = sum(math.comb(discordant, k) for k in range(min(only_first, only_second) + 1))
    return only_first, only_second, min(1.0, 2 * tail / 2**discordant)
