---
title: 单元 05 示例工程：数学概率与优化实验
tags:
  - example
  - mathematics
  - probability
  - optimization
status: published
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# 单元 05 示例工程：数学概率与优化实验

> [!nav] 页面导航
> [[01_学习指南/05_数学概率与优化/00 数学概率优化学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/05_数学概率与优化/逐讲学习/01 向量矩阵与张量形状|从第一讲开始：向量矩阵与张量形状]]

这是单元 05 的最小可运行工程。核心数学源码放在 `app/`，分布与特征值演示脚本放在工程根目录，测试放在 `tests/`。基础实验使用 NumPy；PyTorch 自动求导验证是可选脚本。

## 准备环境

本单元使用仓库根目录共享环境中的 NumPy。先按根目录 [README](../../../90_参考与维护/01 使用与环境/01 共享Python环境与运行约定.md#共享-python-环境) 配置环境；在本目录运行检查：

~~~powershell
..\..\..\.venv\Scripts\python.exe -c "import numpy; print(numpy.__version__)"
~~~

如果提示找不到 NumPy，先确认所选解释器指向仓库根目录的共享环境，再检查根目录依赖清单是否已安装。

## 运行基础检查

[[01_学习指南/05_数学概率与优化/逐讲学习/01 向量矩阵与张量形状|矩阵第 1 讲]]提供 `lesson_01_matrix.py`、`lesson_01_shapes.py`、`lesson_01_batch.py` 的完整代码；[[01_学习指南/05_数学概率与优化/逐讲学习/02 按轴计算并分清数组视图与副本|数组详细课]]提供轴、复制与标准化三个实验；[[01_学习指南/05_数学概率与优化/逐讲学习/05 从指数与对数走到稳定softmax|softmax 详细课]]提供单行、批量稳定计算与非法输入三个实验。这些脚本由学习者在本工程目录按正文创建，使用共享解释器运行，均为 CPU NumPy／Python 操作。

[[01_学习指南/05_数学概率与优化/逐讲学习/09 梯度下降与学习率|第 9 讲：梯度下降与学习率]]先在本目录创建 `lesson_05_rates.py`，观察三种步长前三次更新，并在同一文件追加单调性检查；二维练习另存 `lesson_05_two_parameters.py`。它们由正文逐步指导创建，使用共享解释器运行，示例不需要额外依赖。检查时比较参数与损失，不能把坐标缩小直接当成总损失下降。

~~~powershell
..\..\..\.venv\Scripts\python.exe -m unittest discover -s tests -v
..\..\..\.venv\Scripts\python.exe -m compileall -q app tests
~~~

预期所有 unittest 通过。不同 NumPy 版本可能产生微小浮点差异，测试使用容差比较。

## 代码导航

- [eigen_demo.py](./eigen_demo.py)：实对称矩阵输入检查、特征对残差、重构和奇异值对照；导入不执行实验。
- [test_eigen.py](./tests/test_eigen.py)：已知特征对、正交归一、重复／负／零值、只读输入与非法输入检查。

- [app/math_basics.py](./app/math_basics.py)：向量、矩阵、概率、信息论、梯度、梯度下降和 SVD 示例；信息论使用 bit，KL 以对数相减避免比值溢出。
- [app/optimization.py](./app/optimization.py)：一维二次函数的梯度下降过程。
- [app/optional_autograd.py](./app/optional_autograd.py)：存在 PyTorch 时验证自动求导，没有安装时输出提示。
- [app/distributions.py](./app/distributions.py)：概率分布补充课的二项概率与总体统计，使用标准库。
- [distribution_demo.py](./distribution_demo.py)：运行离散次数、两组均值／标准差及假设正态区间的完整示例。
- [tests/test_math_basics.py](./tests/test_math_basics.py)：形状、概率、损失、梯度和低秩近似测试；包含软目标、KL 方向、极小正概率、零概率及单位换算。
- [tests/test_distributions.py](./tests/test_distributions.py)：序列穷举、概率边界、总体方差约定与正态模型核对。
- [numerics.py](./app/numerics.py)：非空二维有限实数分数的逐行 softmax；不修改输入，返回 float64，不提供自动求导或注意力 mask 接口。
- [test_numerics.py](./tests/test_numerics.py)：已知概率、行归一化、共同平移、极端值、只读输入与失败契约。

## 特征值与二维变换练习

在本目录运行 `..\..\..\.venv\Scripts\python.exe eigen_demo.py`。按 [[01_学习指南/05_数学概率与优化/逐讲学习/10 用二维变换理解特征值与特征向量|特征值详细课]]创建 `lesson_05_eigen_pairs.py`、`lesson_05_eigen_reconstruction.py`、`lesson_05_eigen_vs_svd.py`、`lesson_05_eigen_boundary.py`；它们是学习者练习文件，不是已有源码入口。完整代码、命令、输出、常见错误和练习答案均在正文。

`decompose_symmetric_matrix` 接受非空有限实方阵，转成 float64，严格检查对称后返回升序特征值与列特征向量。不修复近似对称输入，不接受复数或批量矩阵；这是教学接口限制。底层求解不收敛时保留 NumPy 异常，超出浮点范围的特征值明确失败。残差使用原输入检查，本课小矩阵取 1e-10 容差，不把该阈值推广到任意尺度。全部实验在 CPU 上运行，复用已有 NumPy，不需新增依赖。

## 信息论与下一词损失练习

信息论练习入口见 [[01_学习指南/05_数学概率与优化/逐讲学习/06 熵交叉熵与KL散度|第 6 讲：熵交叉熵与KL散度]]与 [[01_学习指南/05_数学概率与优化/逐讲学习/07 对齐下一个词并只统计有效损失|下一词损失详细课]]。按正文在本目录自行创建 `lesson_03_information.py`、`lesson_03_boundaries.py`、`lesson_03_binary.py`、`lesson_03_token_alignment.py`、`lesson_03_masked_mean.py`；这些名称是学习者练习文件，不是已提交的源码文件。每个脚本都有完整代码与预期输出，使用 `..\..\..\.venv\Scripts\python.exe 文件名.py` 运行。概率函数复用已有 NumPy 环境；二分类答案与 token 练习只用标准库，均不需要 GPU 或模型。

## 概率分布补充课

在本工程运行 `..\..\..\.venv\Scripts\python.exe distribution_demo.py`；对应讲解见 [[01_学习指南/05_数学概率与优化/逐讲学习/04 用具体数据理解概率分布|概率分布详细课]]。二项模型要求固定次数、独立且同成功概率；统计函数把输入列表当完整总体，方差除以 n；NormalDist 例子是指定参数的假设模型，没有拟合真实数据。脚本运行无需额外包、网络或 GPU。

## 可选的 PyTorch 验证

SVD 学习时先按 [[01_学习指南/05_数学概率与优化/逐讲学习/11 SVD低秩近似与综合速查|第 11 讲：SVD低秩近似与综合速查]] 在本目录创建 `lesson_06_svd.py`、`lesson_06_exact.py` 并分别运行。前者核对截断误差 1／0，后者展示舍弃零奇异值仍可精确重构；无需新增依赖。脚本由学习者按正文创建，完整函数在上方源码导航的 `math_basics.py`。

如果已经按仓库根目录说明安装 PyTorch，可执行：

~~~powershell
..\..\..\.venv\Scripts\python.exe app/optional_autograd.py
~~~

若提示找不到 PyTorch，请回到根目录 README 按设备选择 CPU 或 CUDA 安装方式，再使用同一个共享解释器运行。
