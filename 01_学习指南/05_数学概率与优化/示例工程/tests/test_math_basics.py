import math
import unittest

import numpy as np

from app.math_basics import (
    bayes_posterior,
    bernoulli_mle,
    cross_entropy,
    dot,
    entropy,
    finite_difference_gradient,
    kl_divergence,
    matrix_multiply,
    quadratic_gradient,
    quadratic_loss,
    truncated_svd,
    vector_norm,
)
from app.optimization import quadratic_descent


class LinearAlgebraTests(unittest.TestCase):
    def test_dot_matrix_and_norm(self):
        self.assertAlmostEqual(dot([1, 2, 3], [4, 5, 6]), 32)
        result = matrix_multiply([[1, 2], [3, 4]], [[2], [1]])
        np.testing.assert_allclose(result, [[4], [10]])
        self.assertAlmostEqual(vector_norm([3, 4]), 5)
        self.assertAlmostEqual(vector_norm([-2, 3], order=1), 5)

    def test_shape_mismatch_is_explicit(self):
        with self.assertRaisesRegex(ValueError, "same shape"):
            dot([1, 2], [1])
        with self.assertRaisesRegex(ValueError, "inner"):
            matrix_multiply([[1, 2]], [[1, 2]])


class ProbabilityAndInformationTests(unittest.TestCase):
    def test_bayes_and_mle(self):
        posterior = bayes_posterior(0.01, 0.99, 0.05)
        self.assertAlmostEqual(posterior, 1 / 6, places=5)
        self.assertAlmostEqual(bernoulli_mle([1, 1, 0, 1, 0]), 0.6)

    def test_bayes_rejects_invalid_probabilities(self):
        with self.assertRaisesRegex(ValueError, "between 0 and 1"):
            bayes_posterior(-0.1, 0.9, 0.1)

    def test_entropy_cross_entropy_and_kl(self):
        target = [1.0, 0.0]
        predicted = [0.8, 0.2]
        self.assertAlmostEqual(entropy([0.5, 0.5]), np.log2(2))
        self.assertAlmostEqual(cross_entropy(target, predicted), -np.log2(0.8))
        self.assertAlmostEqual(
            cross_entropy(target, predicted) - entropy(target),
            kl_divergence(target, predicted),
        )

    def test_invalid_distributions_are_rejected(self):
        with self.assertRaises(ValueError):
            entropy([0.2, 0.2])
        with self.assertRaises(ValueError):
            cross_entropy([1.0, 0.0], [0.0, 1.0])

    def test_zero_target_terms_do_not_take_logarithm_of_zero(self):
        self.assertEqual(cross_entropy([1.0, 0.0], [1.0, 0.0]), 0.0)
        target = [0.0, 0.25, 0.75]
        predicted = [0.0, 0.5, 0.5]
        self.assertAlmostEqual(cross_entropy(target, predicted), 1.0)
        self.assertAlmostEqual(
            cross_entropy(target, predicted) - entropy(target),
            kl_divergence(target, predicted),
        )

    def test_soft_target_identity_and_kl_direction(self):
        target = [0.75, 0.25]
        predicted = [0.5, 0.5]
        self.assertAlmostEqual(entropy(target), 0.8112781244591328)
        self.assertAlmostEqual(cross_entropy(target, predicted), 1.0)
        self.assertAlmostEqual(kl_divergence(target, predicted), 0.18872187554086717)
        self.assertAlmostEqual(kl_divergence(predicted, target), 0.2075187496394219)
        self.assertAlmostEqual(
            cross_entropy(target, predicted) - entropy(target),
            kl_divergence(target, predicted),
        )

    def test_tiny_positive_prediction_has_finite_kl(self):
        tiny = math.nextafter(0.0, 1.0)
        loss = kl_divergence([1.0, 0.0], [tiny, 1.0])
        self.assertTrue(math.isfinite(loss))
        self.assertEqual(loss, -math.log2(tiny))
        self.assertEqual(loss, cross_entropy([1.0, 0.0], [tiny, 1.0]))

    def test_probability_boundaries_are_rejected(self):
        for values in ([], [-0.1, 1.1], [float("nan"), 1.0], [float("inf"), 0.0]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                entropy(values)

    def test_information_functions_reject_mismatched_lengths(self):
        for function in (cross_entropy, kl_divergence):
            with (
                self.subTest(function=function),
                self.assertRaisesRegex(ValueError, "same length"),
            ):
                function([1.0], [0.5, 0.5])

    def test_information_functions_reject_missing_predicted_support(self):
        for function in (cross_entropy, kl_divergence):
            with (
                self.subTest(function=function),
                self.assertRaisesRegex(ValueError, "positive"),
            ):
                function([0.5, 0.5], [1.0, 0.0])

    def test_bit_and_nat_conversion(self):
        bits = cross_entropy([0.0, 1.0], [0.2, 0.8])
        self.assertAlmostEqual(bits * math.log(2.0), -math.log(0.8))


class OptimizationAndSvdTests(unittest.TestCase):
    def test_finite_difference_matches_analytic_gradient(self):
        analytic = quadratic_gradient(1.5)
        numeric = finite_difference_gradient(quadratic_loss, 1.5)
        self.assertAlmostEqual(numeric, analytic, places=5)
        for epsilon in (0, float("nan"), float("inf")):
            with (
                self.subTest(epsilon=epsilon),
                self.assertRaisesRegex(
                    ValueError,
                    "finite and positive",
                ),
            ):
                finite_difference_gradient(quadratic_loss, 1.5, epsilon)

    def test_descent_reduces_quadratic_loss(self):
        history = quadratic_descent(start=0, learning_rate=0.1, steps=8)
        self.assertLess(history[-1][1], history[0][1])
        self.assertAlmostEqual(history[-1][0], 3 * (1 - 0.8**8), places=5)
        with self.assertRaisesRegex(ValueError, "finite and positive"):
            quadratic_descent(start=0, learning_rate=float("nan"), steps=1)

    def test_svd_rank_one_approximation(self):
        matrix = np.array([[3.0, 0.0], [0.0, 1.0]])
        approximation = truncated_svd(matrix, rank=1)
        self.assertAlmostEqual(np.linalg.norm(matrix - approximation), 1.0)
        with self.assertRaises(ValueError):
            truncated_svd(matrix, rank=0)


if __name__ == "__main__":
    unittest.main()
