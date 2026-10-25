"""实对称矩阵的特征值实验；在本目录运行，使用共享 NumPy 环境。"""

import numpy as np


def decompose_symmetric_matrix(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """分解非空、有限、严格对称的实方阵，返回升序特征值与列特征向量。"""
    matrix = np.asarray(matrix)
    if matrix.ndim != 2 or matrix.shape[0] == 0:
        raise ValueError("请输入非空二维方阵。")
    if matrix.shape[0] != matrix.shape[1]:
        raise ValueError("方阵的行数与列数必须相同。")
    if np.iscomplexobj(matrix):
        raise ValueError("本教学接口只接受实数矩阵。")
    matrix = np.asarray(matrix, dtype=np.float64)
    if not np.all(np.isfinite(matrix)):
        raise ValueError("矩阵元素必须是有限实数。")
    # eigh 默认只读取下三角；先检查，避免悄悄分解另一个对称矩阵。
    if not np.array_equal(matrix, matrix.T):
        raise ValueError("矩阵必须严格对称；请核对上下三角元素。")
    eigenvalues, eigenvectors = np.linalg.eigh(matrix)
    if not np.all(np.isfinite(eigenvalues)):
        raise FloatingPointError("特征值超出浮点范围；请检查矩阵尺度。")
    return eigenvalues, eigenvectors


def main() -> None:
    matrix = np.array([[2.0, 1.0], [1.0, 2.0]])
    eigenvalues, eigenvectors = decompose_symmetric_matrix(matrix)
    print("特征值：", eigenvalues.tolist())
    for index in range(len(eigenvalues)):
        eigenvalue = eigenvalues[index]
        eigenvector = eigenvectors[:, index]
        residual = matrix @ eigenvector - eigenvalue * eigenvector
        print("特征对", index, "残差范数", f"{np.linalg.norm(residual):.3e}")

    reconstructed = eigenvectors @ np.diag(eigenvalues) @ eigenvectors.T
    reconstruction_error = np.linalg.norm(matrix - reconstructed)
    print("重构误差小于 1e-10：", bool(reconstruction_error < 1e-10))

    negative_matrix = np.diag([-2.0, 1.0])
    negative_values, _ = decompose_symmetric_matrix(negative_matrix)
    singular_values = np.linalg.svd(negative_matrix, compute_uv=False)
    print("含负值的特征值：", negative_values.tolist())
    print("奇异值：", singular_values.tolist())


if __name__ == "__main__":
    main()
