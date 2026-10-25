import unittest

import numpy as np

from app.numerics import softmax_rows


class SoftmaxTests(unittest.TestCase):
    def test_equal_scores_and_known_ratio(self):
        scores = np.array([[0.0, 0.0], [0.0, np.log(3.0)]])
        np.testing.assert_allclose(softmax_rows(scores), [[0.5, 0.5], [0.25, 0.75]])

    def test_each_row_is_normalized_independently(self):
        scores = np.array([[1.0, 2.0, 3.0], [-5.0, 7.0, 2.0]])
        result = softmax_rows(scores)
        self.assertEqual(result.shape, scores.shape)
        self.assertTrue(np.isfinite(result).all())
        self.assertTrue((result >= 0).all())
        np.testing.assert_allclose(result.sum(axis=1), [1.0, 1.0])
        np.testing.assert_allclose(result[0], softmax_rows(scores[:1])[0])

    def test_common_offset_does_not_change_probabilities(self):
        scores = np.array([[1.0, 2.0, 3.0]])
        np.testing.assert_allclose(softmax_rows(scores), softmax_rows(scores + 1000.0))

    def test_extreme_finite_values_allow_underflow_without_invalid_results(self):
        scores = np.array([[1e308, -1e308], [-1000.0, -1000.0]])
        with np.errstate(all="raise"):
            result = softmax_rows(scores)
        np.testing.assert_allclose(result, [[1.0, 0.0], [0.5, 0.5]])

    def test_input_is_unchanged_and_single_class_is_one(self):
        scores = np.array([[2.0], [-4.0]])
        original = scores.copy()
        scores.setflags(write=False)
        np.testing.assert_allclose(softmax_rows(scores), [[1.0], [1.0]])
        np.testing.assert_array_equal(scores, original)

    def test_rejects_empty_and_wrong_dimensions(self):
        for scores in (
            np.array(1.0),
            np.ones(3),
            np.ones((1, 1, 1)),
            np.empty((0, 2)),
            np.empty((2, 0)),
        ):
            with (
                self.subTest(shape=scores.shape),
                self.assertRaisesRegex(ValueError, "two-dimensional"),
            ):
                softmax_rows(scores)

    def test_rejects_nonfinite_and_complex_inputs(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(ValueError, "finite"),
            ):
                softmax_rows(np.array([[value, 0.0]]))
        with self.assertRaisesRegex(ValueError, "real-valued"):
            softmax_rows(np.array([[1.0 + 2.0j]]))


if __name__ == "__main__":
    unittest.main()
