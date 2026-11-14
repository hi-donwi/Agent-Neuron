"""Classification heads over fixed embeddings: label centroids and softmax regression.

Everything here is deterministic: no random initialisation and no sampling, so the same
inputs give the same head on any machine up to floating-point rounding.
"""

import math

import numpy as np


def unit_rows(matrix: np.ndarray) -> np.ndarray:
    """Scale each row to length one. A zero row stays zero."""
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.where(norms == 0.0, 1.0, norms)


def centroids(vectors: np.ndarray, labels: np.ndarray, classes: int) -> np.ndarray:
    """One unit vector per class: the mean of that class's unit vectors."""
    unit = unit_rows(vectors)
    result = np.zeros((classes, vectors.shape[1]), dtype=np.float64)
    for index in range(classes):
        members = unit[labels == index]
        if len(members) == 0:
            raise ValueError(f"class {index} has no examples")
        result[index] = members.mean(axis=0)
    return unit_rows(result)


def softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    exponent = np.exp(shifted)
    return exponent / exponent.sum(axis=1, keepdims=True)


def fit_softmax(
    vectors: np.ndarray,
    labels: np.ndarray,
    classes: int,
    l2: float,
    steps: int = 5000,
    rate: float = 0.05,
    tolerance: float = 1e-5,
) -> tuple[np.ndarray, np.ndarray]:
    """Multinomial logistic regression: weights (classes x dim) and bias (classes).

    Minimises mean cross-entropy plus l2/2 times the squared weights (the bias is not
    penalised) with full-batch Adam from zero, and stops once the largest gradient entry
    falls below the tolerance. The objective is convex, so the starting point and the
    optimiser do not change which head it converges to.
    """
    data = np.asarray(vectors, dtype=np.float64)
    count, dim = data.shape
    target = np.zeros((count, classes), dtype=np.float64)
    target[np.arange(count), labels] = 1.0

    weights = np.zeros((classes, dim), dtype=np.float64)
    bias = np.zeros(classes, dtype=np.float64)
    moment_w = np.zeros_like(weights)
    moment_b = np.zeros_like(bias)
    second_w = np.zeros_like(weights)
    second_b = np.zeros_like(bias)
    beta1, beta2, epsilon = 0.9, 0.999, 1e-8

    for step in range(1, steps + 1):
        residual = softmax(data @ weights.T + bias) - target
        gradient_w = residual.T @ data / count + l2 * weights
        gradient_b = residual.mean(axis=0)
        if max(np.abs(gradient_w).max(), np.abs(gradient_b).max()) < tolerance:
            break
        moment_w = beta1 * moment_w + (1 - beta1) * gradient_w
        moment_b = beta1 * moment_b + (1 - beta1) * gradient_b
        second_w = beta2 * second_w + (1 - beta2) * gradient_w**2
        second_b = beta2 * second_b + (1 - beta2) * gradient_b**2
        scale = rate * math.sqrt(1 - beta2**step) / (1 - beta1**step)
        weights -= scale * moment_w / (np.sqrt(second_w) + epsilon)
        bias -= scale * moment_b / (np.sqrt(second_b) + epsilon)
    return weights, bias


def fit_temperature(logits: np.ndarray, labels: np.ndarray) -> float:
    """The temperature T that minimises cross-entropy of softmax(logits / T).

    Golden-section search over log T between 0.01 and 100; the loss is unimodal in log T.
    """
    rows = np.arange(len(labels))

    def loss(log_temperature: float) -> float:
        scaled = logits / math.exp(log_temperature)
        scaled = scaled - scaled.max(axis=1, keepdims=True)
        log_probability = scaled - np.log(np.exp(scaled).sum(axis=1, keepdims=True))
        return float(-log_probability[rows, labels].mean())

    ratio = (math.sqrt(5) - 1) / 2
    low, high = math.log(0.01), math.log(100.0)
    left = high - ratio * (high - low)
    right = low + ratio * (high - low)
    loss_left, loss_right = loss(left), loss(right)
    for _ in range(60):
        if loss_left < loss_right:
            high, right, loss_right = right, left, loss_left
            left = high - ratio * (high - low)
            loss_left = loss(left)
        else:
            low, left, loss_left = left, right, loss_right
            right = low + ratio * (high - low)
            loss_right = loss(right)
    return math.exp((low + high) / 2)
