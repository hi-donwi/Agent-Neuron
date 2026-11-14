import numpy as np
import pytest

from neuron_lab.head import centroids, fit_softmax, fit_temperature, softmax, unit_rows


def test_unit_rows_scales_each_row_to_length_one_and_leaves_a_zero_row_alone():
    result = unit_rows(np.array([[3.0, 4.0], [0.0, 0.0]]))

    assert result[0] == pytest.approx([0.6, 0.8])
    assert result[1] == pytest.approx([0.0, 0.0])


def test_centroids_are_the_unit_mean_of_each_class_in_class_order():
    vectors = np.array([[1.0, 0.0], [0.0, 1.0], [0.0, 2.0], [0.0, 4.0]])
    labels = np.array([1, 1, 0, 0])

    result = centroids(vectors, labels, classes=2)

    assert result[0] == pytest.approx([0.0, 1.0])
    assert result[1] == pytest.approx([2**-0.5, 2**-0.5])


def test_centroids_refuse_a_class_without_examples():
    with pytest.raises(ValueError):
        centroids(np.array([[1.0, 0.0]]), np.array([0]), classes=2)


def test_softmax_rows_sum_to_one_and_survive_large_logits():
    result = softmax(np.array([[1000.0, 1000.0], [0.0, np.log(3.0)]]))

    assert result[0] == pytest.approx([0.5, 0.5])
    assert result[1] == pytest.approx([0.25, 0.75])


def separable_problem():
    rng = np.random.default_rng(7)
    centres = np.array([[2.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 2.0]])
    labels = np.repeat(np.arange(3), 40)
    vectors = centres[labels] + rng.normal(scale=0.2, size=(120, 3))
    return vectors, labels


def test_fit_softmax_separates_a_separable_problem():
    vectors, labels = separable_problem()

    weights, bias = fit_softmax(vectors, labels, classes=3, l2=1e-3)

    assert weights.shape == (3, 3)
    assert bias.shape == (3,)
    assert ((vectors @ weights.T + bias).argmax(axis=1) == labels).all()


def test_fit_softmax_is_deterministic():
    vectors, labels = separable_problem()

    first = fit_softmax(vectors, labels, classes=3, l2=1e-3)
    second = fit_softmax(vectors, labels, classes=3, l2=1e-3)

    assert np.array_equal(first[0], second[0])
    assert np.array_equal(first[1], second[1])


def test_a_stronger_penalty_gives_smaller_weights():
    vectors, labels = separable_problem()

    loose, _ = fit_softmax(vectors, labels, classes=3, l2=1e-4)
    tight, _ = fit_softmax(vectors, labels, classes=3, l2=1e-1)

    assert np.linalg.norm(tight) < np.linalg.norm(loose)


def test_fit_softmax_reaches_the_optimum_of_its_objective():
    vectors, labels = separable_problem()
    l2 = 1e-2

    weights, bias = fit_softmax(vectors, labels, classes=3, l2=l2)

    # At the optimum the gradient of mean cross-entropy plus the penalty vanishes.
    residual = softmax(vectors @ weights.T + bias)
    residual[np.arange(len(labels)), labels] -= 1.0
    gradient = residual.T @ vectors / len(labels) + l2 * weights
    assert np.abs(gradient).max() < 1e-3
    assert np.abs(residual.mean(axis=0)).max() < 1e-3


def test_fit_temperature_recovers_the_factor_that_made_logits_overconfident():
    rng = np.random.default_rng(11)
    true_logits = rng.normal(scale=2.0, size=(4000, 5))
    probabilities = softmax(true_logits)
    labels = np.array([rng.choice(5, p=row) for row in probabilities])

    assert fit_temperature(true_logits, labels) == pytest.approx(1.0, abs=0.1)
    assert fit_temperature(true_logits * 4.0, labels) == pytest.approx(4.0, abs=0.4)
    assert fit_temperature(true_logits / 4.0, labels) == pytest.approx(0.25, abs=0.03)
