"""Optimization process examples."""

from __future__ import annotations

import math

from .math_basics import quadratic_gradient, quadratic_loss


def quadratic_descent(
    start: float,
    learning_rate: float,
    steps: int,
    target: float = 3.0,
) -> list[tuple[float, float]]:
    if not math.isfinite(learning_rate) or learning_rate <= 0:
        raise ValueError("learning_rate must be finite and positive")
    if steps < 0:
        raise ValueError("steps must be non-negative")
    value = start
    history = [(value, quadratic_loss(value, target))]
    for _ in range(steps):
        value -= learning_rate * quadratic_gradient(value, target)
        history.append((value, quadratic_loss(value, target)))
    return history
