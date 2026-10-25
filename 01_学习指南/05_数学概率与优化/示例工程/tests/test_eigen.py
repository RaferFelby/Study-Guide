import unittest

import numpy as np

from eigen_demo import decompose_symmetric_matrix


class SymmetricEigenTests(unittest.TestCase):
    def test_known_values_and_column_eigenpairs(self):
        matrix = np.array([[2.0, 1.0], [1.0, 2.0]])
        values, vectors = decompose_symmetric_matrix(matrix)
        np.testing.assert_allclose(values, [1.0, 3.0], atol=1e-12)
        for index in range(2):
            np.testing.assert_allclose(
                matrix @ vectors[:, index],
                values[index] * vectors[:, index],
                atol=1e-12,
            )

    def test_orthonormal_columns_and_reconstruction(self):
        matrix = np.array([[4.0, 1.0, 2.0], [1.0, 3.0, 0.0], [2.0, 0.0, -1.0]])
        values, vectors = decompose_symmetric_matrix(matrix)
        np.testing.assert_allclose(vectors.T @ vectors, np.eye(3), atol=1e-12)
        reconstructed = vectors @ np.diag(values) @ vectors.T
        np.testing.assert_allclose(reconstructed, matrix, atol=1e-12)

    def test_negative_and_zero_values_are_valid(self):
        values, _ = decompose_symmetric_matrix(np.diag([-2.0, 0.0, 1.0]))
        np.testing.assert_allclose(values, [-2.0, 0.0, 1.0], atol=1e-12)

    def test_repeated_values_do_not_require_a_particular_basis(self):
        matrix = 2.0 * np.eye(3)
        values, vectors = decompose_symmetric_matrix(matrix)
        np.testing.assert_allclose(values, [2.0, 2.0, 2.0], atol=1e-12)
        np.testing.assert_allclose(matrix @ vectors, vectors * values, atol=1e-12)
        np.testing.assert_allclose(vectors.T @ vectors, np.eye(3), atol=1e-12)

    def test_zero_matrix_has_zero_values_and_valid_basis(self):
        values, vectors = decompose_symmetric_matrix(np.zeros((2, 2)))
        np.testing.assert_allclose(values, [0.0, 0.0], atol=1e-12)
        np.testing.assert_allclose(vectors.T @ vectors, np.eye(2), atol=1e-12)

    def test_one_by_one_matrix(self):
        values, vectors = decompose_symmetric_matrix(np.array([[5.0]]))
        np.testing.assert_allclose(values, [5.0])
        np.testing.assert_allclose(np.abs(vectors), [[1.0]])

    def test_integer_readonly_input_is_unchanged(self):
        matrix = np.array([[2, 1], [1, 2]])
        original = matrix.copy()
        matrix.setflags(write=False)
        values, vectors = decompose_symmetric_matrix(matrix)
        np.testing.assert_array_equal(matrix, original)
        self.assertEqual(values.dtype, np.float64)
        self.assertEqual(vectors.dtype, np.float64)

    def test_rejects_empty_and_wrong_dimensions(self):
        for matrix in (
            np.array(1.0),
            np.ones(2),
            np.ones((1, 2, 2)),
            np.empty((0, 0)),
            np.empty((0, 2)),
            np.ones((2, 3)),
        ):
            with self.subTest(shape=matrix.shape), self.assertRaises(ValueError):
                decompose_symmetric_matrix(matrix)

    def test_rejects_nonfinite_values(self):
        for value in (np.nan, np.inf, -np.inf):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "有限"):
                decompose_symmetric_matrix(np.diag([value, 1.0]))

    def test_rejects_complex_values(self):
        with self.assertRaisesRegex(ValueError, "实数"):
            decompose_symmetric_matrix(np.array([[1.0 + 1.0j]]))

    def test_rejects_asymmetry_including_small_mismatch(self):
        for upper in (2.0, 1.0 + 1e-13):
            with (
                self.subTest(upper=upper),
                self.assertRaisesRegex(ValueError, "严格对称"),
            ):
                decompose_symmetric_matrix(np.array([[2.0, upper], [1.0, 2.0]]))

    def test_singular_values_do_not_keep_eigenvalue_signs(self):
        matrix = np.diag([-2.0, 1.0])
        values, _ = decompose_symmetric_matrix(matrix)
        singular_values = np.linalg.svd(matrix, compute_uv=False)
        np.testing.assert_allclose(values, [-2.0, 1.0])
        np.testing.assert_allclose(singular_values, [2.0, 1.0])


if __name__ == "__main__":
    unittest.main()
