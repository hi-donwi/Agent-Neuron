import pytest

from neuron_lab.metrics import (
    auroc,
    expected_calibration_error,
    paired_sign_test,
    percentile,
    threshold_for_false_accept,
    wilson_interval,
)


def test_wilson_interval_matches_the_textbook_value_for_eight_of_ten():
    low, high = wilson_interval(8, 10)

    assert low == pytest.approx(0.4902, abs=1e-4)
    assert high == pytest.approx(0.9433, abs=1e-4)


def test_wilson_interval_stays_inside_zero_and_one_at_the_extremes():
    assert wilson_interval(0, 20)[0] == 0.0
    assert wilson_interval(20, 20)[1] == 1.0
    assert wilson_interval(20, 20)[0] < 1.0


def test_wilson_interval_refuses_an_empty_sample():
    with pytest.raises(ValueError):
        wilson_interval(0, 0)


def test_auroc_is_one_when_every_positive_outscores_every_negative():
    assert auroc([0.9, 0.8], [0.2, 0.1]) == 1.0


def test_auroc_is_zero_when_the_order_is_reversed():
    assert auroc([0.1, 0.2], [0.8, 0.9]) == 0.0


def test_auroc_counts_a_tie_as_half():
    assert auroc([0.5], [0.5]) == 0.5
    # Pairs: (0.7>0.5)=1, (0.7>0.7)=0.5, (0.5=0.5)=0.5, (0.5<0.7)=0 -> 2.0 of 4.
    assert auroc([0.7, 0.5], [0.5, 0.7]) == 0.5


def test_auroc_refuses_an_empty_side():
    with pytest.raises(ValueError):
        auroc([], [0.1])


def test_calibration_error_is_zero_when_confidence_equals_accuracy():
    confidences = [0.75, 0.75, 0.75, 0.75]
    correct = [True, True, True, False]

    assert expected_calibration_error(confidences, correct) == pytest.approx(0.0)


def test_calibration_error_is_the_gap_for_an_overconfident_model():
    confidences = [1.0, 1.0, 1.0, 1.0]
    correct = [True, False, True, False]

    assert expected_calibration_error(confidences, correct) == pytest.approx(0.5)


def test_calibration_error_weights_each_bin_by_its_share():
    # Bin near 0.95: one item, wrong -> gap 0.95. Bin near 0.55: three items, all
    # right -> gap 0.45. Weighted: 0.25 * 0.95 + 0.75 * 0.45.
    confidences = [0.95, 0.55, 0.55, 0.55]
    correct = [False, True, True, True]

    assert expected_calibration_error(confidences, correct) == pytest.approx(0.575)


def test_percentile_uses_the_nearest_rank():
    assert percentile(list(range(1, 101)), 95) == 95
    assert percentile([4, 1, 3, 2], 50) == 2
    assert percentile([7], 95) == 7


def test_percentile_refuses_an_empty_sample():
    with pytest.raises(ValueError):
        percentile([], 95)


def test_threshold_lets_through_at_most_the_allowed_share():
    scores = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

    threshold = threshold_for_false_accept(scores, 0.2)

    assert threshold == 0.8
    assert sum(score > threshold for score in scores) == 2


def test_threshold_is_conservative_when_scores_tie():
    # Allowing one of four through would admit all three tied scores; none may pass.
    scores = [0.9, 0.9, 0.9, 0.1]

    threshold = threshold_for_false_accept(scores, 0.25)

    assert sum(score > threshold for score in scores) == 0


def test_threshold_with_a_zero_rate_admits_nothing():
    scores = [0.3, 0.6]

    assert threshold_for_false_accept(scores, 0.0) == 0.6


def test_paired_sign_test_counts_only_the_cases_where_two_arms_disagree():
    first = [True, True, True, False, False, True]
    second = [True, False, False, False, True, False]

    only_first, only_second, p_value = paired_sign_test(first, second)

    assert (only_first, only_second) == (3, 1)
    # Two-sided exact binomial with 4 discordant pairs: 2 * (C(4,0) + C(4,1)) / 16.
    assert p_value == pytest.approx(0.625)


def test_paired_sign_test_is_one_when_the_arms_never_disagree_or_split_evenly():
    assert paired_sign_test([True, False], [True, False]) == (0, 0, 1.0)
    assert paired_sign_test([True, False], [False, True]) == (1, 1, 1.0)


def test_paired_sign_test_is_small_when_one_arm_wins_every_disagreement():
    only_first, only_second, p_value = paired_sign_test([True] * 10, [False] * 10)

    assert (only_first, only_second) == (10, 0)
    assert p_value == pytest.approx(2 / 1024)


def test_paired_sign_test_refuses_unequal_lengths():
    with pytest.raises(ValueError):
        paired_sign_test([True], [True, False])
