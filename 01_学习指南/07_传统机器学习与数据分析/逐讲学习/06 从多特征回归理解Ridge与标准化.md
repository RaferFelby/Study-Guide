---
title: 第 6 讲：从多特征回归理解Ridge与标准化
tags: [lesson, regression, ridge, beginner]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 6 讲：从多特征回归理解Ridge与标准化

> [!nav] 页面导航
> [[01_学习指南/07_传统机器学习与数据分析/00 传统机器学习与数据分析学习地图#学习顺序|单元 07：传统机器学习与数据分析]] · [[01_学习指南/07_传统机器学习与数据分析/逐讲学习/05 用交叉验证比较树模型|上一讲]] · [[01_学习指南/07_传统机器学习与数据分析/逐讲学习/07 公平比较回归模型并检查残差|下一讲]]

## 先做什么，学完怎样判断

先完成 [[01_学习指南/07_传统机器学习与数据分析/逐讲学习/03 拟合一条直线并读懂回归指标|一维回归与指标]]，会区分特征、目标、系数、训练与评估；再复习主线第 2、4 讲的 Pipeline 与选模边界。矩阵形状不熟悉时回到 [[01_学习指南/05_数学概率与优化/逐讲学习/01 向量矩阵与张量形状|矩阵形状]]。

本课顺序是“多列输入 → 手算正则化 → 运行两点示例 → 改单位 → 练习”。先回答：如果把米改成毫米，物理对象没有变，为什么同一个 Ridge 参数可能给出不同预测？读完应能运行反例，再解释标准化怎样改变这个问题。本课不做参数搜索，下一篇才比较模型。

> [!contents]- 本讲导航
> - [[#先做什么，学完怎样判断|先做什么，学完怎样判断]]
> - [[#1. 从一条直线到多个输入|1. 从一条直线到多个输入]]
> - [[#2. Ridge 给拟合目标增加什么|2. Ridge 给拟合目标增加什么]]
> - [[#3. 在 VS Code 验证手算|3. 在 VS Code 验证手算]]
> - [[#4. 为什么单位会影响惩罚|4. 为什么单位会影响惩罚]]
> - [[#5. 练习与答案|5. 练习与答案]]
> - [[#6. 常见错误与下一步|6. 常见错误与下一步]]

## 1. 从一条直线到多个输入

之前是 `预测 = b + w × 文件大小`。现在同时观察页数和附件数：

`预测耗时 = b + w₁ × 页数 + w₂ × 附件数`

`b` 是截距，`w₁/w₂` 是每一列的系数。下标 1、2 表示对应第几列，不表示平方。把这些输入放进矩阵 X：每行是一个文档，每列是一个特征；n 个样本、d 个特征时形状为 `[n,d]`。目标 y 只有一种耗时，形状为 `[n]`。**多个输入特征不等于多个预测目标**。

例如 b=5、页数系数 0.5、附件系数 2，10 页、3 个附件的预测为 `5+0.5×10+2×3=16` 分钟。下面可以直接运行这个计算：

```python
import numpy as np

features = np.array([[10, 3], [4, 0]], dtype=float)
weights = np.array([0.5, 2.0])
intercept = 5.0
predictions = features @ weights + intercept
print(predictions.tolist())
```

输出 `[16.0, 7.0]`。`@` 做矩阵与向量相乘：每行对应位置相乘，再相加；加截距时每个预测都加 5。这里系数是人为给定的，没有训练。真实模型要用训练数据估计它们，不能把这个演示当经验结论。

如果页数与字符数几乎同步变化，两列可能表达相近的信息，这叫特征高度相关。许多不同系数组合都能产生相近预测，系数可能对数据扰动敏感。系数大也不自动证明该特征具有因果作用。

## 2. Ridge 给拟合目标增加什么

普通最小二乘希望训练样本的平方误差总和尽量小。Ridge（岭回归）在这个目标上加入权重平方和的惩罚：

`目标 J = Σ(yᵢ - 预测ᵢ)² + alpha × Σwⱼ²`

`Σ` 表示“把所有对应项加起来”；第一项遍历样本，第二项遍历输入特征的系数。`alpha` 是事先设置的非负数，越大越重视惩罚大权重。带截距的通常用法中，截距不放进此惩罚项。

这里使用 scikit-learn Ridge 的**误差求和**约定。如果另一份教材把第一项除以样本数 n，并写成 `平均平方误差 + λ×权重平方和`，两者等价时应有 `alpha=n×λ`。不能忽略这个差异直接照抄参数数值。[目标与参数依据：Ridge 官方接口](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html)。

惩罚给模型一个偏好：在拟合与权重大小之间折中。这会引入偏差，有时能降低对噪声的敏感性，但并不保证开发集或测试集更准确。不同特征有相关性时，也不能保证 alpha 增大后每一个系数的绝对值都逐项下降。

### 用两个点手算一次

令 x 为 `[-1,1]`，y 为 `[-2,2]`。为便于手算，此处设截距为 0，只学习一个 w。最小二乘得到 w=2，训练误差为 0。

取 alpha=2：

`J(w) = (-2+w)² + (2-w)² + 2w² = 4(w-1)² + 4`

平方项最小为零，因此 w=1 最优，不再是 2。无需先会求导也能判断。

| w | 预测 | 平方误差和 | 惩罚 2w² | 总目标 J |
|---:|---|---:|---:|---:|
| 0 | 0、0 | 8 | 0 | 8 |
| 1 | -1、1 | 2 | 2 | 4 |
| 2 | -2、2 | 0 | 8 | 8 |

Ridge 的训练平方误差更大，却有更小的“误差加惩罚”目标。这是目标变了，不是优化器算错。表中的 J 不是 MAE、RMSE 或测试成绩，不应和它们混报。

## 3. 在 VS Code 验证手算

在 `01_学习指南/07_传统机器学习与数据分析/示例工程` 新建 `lesson_ridge.py`。把下面完整内容保存进去；第 1 节的小例子也可以另存为 `lesson_multiple_inputs.py`。

```python
import numpy as np
from sklearn.linear_model import LinearRegression, Ridge

features = np.array([[-1.0], [1.0]])
targets = np.array([-2.0, 2.0])
for alpha in [0, 2, 20]:
    if alpha == 0:
        model = LinearRegression(fit_intercept=False)
    else:
        model = Ridge(alpha=alpha, fit_intercept=False, solver="svd")
    model.fit(features, targets)
    predictions = model.predict(features)
    print(alpha, round(float(model.coef_[0]), 4), predictions.round(4).tolist())
```

终端也位于这个工程目录，用 `Get-Location` 核对后运行：

```powershell
..\..\..\.venv\Scripts\python.exe lesson_ridge.py
```

三个 `..` 回到仓库根，再使用共享虚拟环境的解释器。无需新建环境或安装依赖。预期：

```text
0 2.0 [-2.0, 2.0]
2 1.0 [-1.0, 1.0]
20 0.1818 [-0.1818, 0.1818]
```

执行顺序是：选择一个模型 → 用同样两点拟合 → 读系数 → 预测。`fit_intercept=False` 只用于这个已居中的小例子，不是一般数据的默认建议。`solver="svd"` 选择一种线性代数求解方法；这里交给库执行，不要求先手写 SVD。alpha=0 的情形直接使用 `LinearRegression`，避免将 Ridge 当无惩罚求解器。

一般 alpha 下，本例解为 `w=4/(2+alpha)`，所以 alpha=20 得 `4/22≈0.1818`。这只适用于当前两点和无截距设定，不能套在任意数据上。

## 4. 为什么单位会影响惩罚

如果把 x 乘以 1000，同一条预测关系所需的系数会除以 1000。平方惩罚因此变为原来的百万分之一，而不是保持不变。Ridge 的惩罚取决于特征尺度。

**标准化**常按每列计算 `z=(x-训练均值)/训练标准差`，使不同列使用相近的数值尺度。`StandardScaler` 在拟合时记录训练列的均值和标准差；后续数据沿用这些数值，不重新计算。它不会把任意分布变成正态分布，也不能自动修复异常值。

本课用标准差的分母 n，即 `sqrt(Σ(x-均值)²/n)`，与 StandardScaler 的约定一致；常量列缩放因子按 1 处理，避免除零。这里对每一列跨样本统计，不要与 Transformer 对单个 token 特征做 LayerNorm 混淆。[依据：StandardScaler](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html)。

新建 `lesson_ridge_units.py`：

```python
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

features = np.array([[-1.0], [1.0]])
targets = np.array([-2.0, 2.0])
for multiplier in [1, 1000]:
    inputs = features * multiplier
    raw_model = Ridge(alpha=2, solver="svd")
    scaled_model = Pipeline(
        [("scaler", StandardScaler()), ("model", Ridge(alpha=2, solver="svd"))]
    )
    raw_model.fit(inputs, targets)
    scaled_model.fit(inputs, targets)
    print("未缩放", multiplier, raw_model.predict(inputs).round(6).tolist())
    print("标准化", multiplier, scaled_model.predict(inputs).round(6).tolist())
```

按前一节命令把文件名换成 `lesson_ridge_units.py` 运行。预期：

```text
未缩放 1 [-1.0, 1.0]
标准化 1 [-1.0, 1.0]
未缩放 1000 [-1.999998, 1.999998]
标准化 1000 [-1.0, 1.0]
```

Pipeline 是按顺序组织步骤的对象：`fit` 时先拟合 scaler 并变换训练输入，再拟合 Ridge；`predict` 时只使用已保存的缩放参数变换输入，再预测。`("scaler", ...)` 的前一项给步骤命名，便于后来读取统计量。原始 x 或放大后的 x，标准化后都变成 `[-1,1]`，所以本例预测一致。

如果以后要看标准化模型的 `coef_`，它对应标准化后的特征。对非恒定列，原单位的系数为 `标准化系数/训练标准差`；截距也要相应调整。不能只取系数、丢掉 scaler，再直接乘原始输入。部署时应保存并使用整个 Pipeline。

## 5. 练习与答案

### 跟做：alpha 换成 6

先用公式预测 w 与两个预测，再修改 `lesson_ridge.py` 的列表加入 6。完成标准：运行前写出 w=0.5、预测 `[-0.5,0.5]`，说明平方误差和与惩罚各是多少。

> [!example]- 参考答案
> `w=4/(2+6)=0.5`；平方误差和为 `1.5²+1.5²=4.5`，惩罚为 `6×0.5²=1.5`，总目标为 6。不同 alpha 下目标本身变了，不要仅比较总目标数字来选 alpha，应在开发数据上比较预先选定的预测指标。

### 独立：新样本是否会改变缩放参数

训练输入 `[1,3]`，新输入 `[100]`。训练均值为 2、标准差为 1，新值应变为 98。先预测，再运行。完成标准：说明为何不能为一个新样本重新 `fit_transform`。

> [!example]- 参考答案
> 保存为 `lesson_scaler_boundary.py`：
> ```python
> from sklearn.preprocessing import StandardScaler
> 
> scaler = StandardScaler().fit([[1.0], [3.0]])
> print(scaler.mean_.tolist(), scaler.scale_.tolist())
> print(scaler.transform([[100.0]]).tolist())
> print(scaler.mean_.tolist())
> ```
> 输出：
> ```text
> [2.0] [1.0]
> [[98.0]]
> [2.0]
> ```
> `transform` 沿用训练统计；在新样本上 `fit_transform` 会重算成均值 100，并破坏后续回归器所学习的输入坐标。数据超出训练范围时，应分析分布变化，不能靠重算 scaler 把问题隐藏起来。

### 迁移：为什么大 alpha 不一定能处理异常目标

若某条耗时目标由 20 误记为 2000，Ridge 会不会因为惩罚权重而自动忽略它？提示：观察目标中的平方误差项有没有变化。完成标准：区分权重正则化与对异常目标的处理。

> [!example]- 参考答案
> 不保证。Ridge 仍使用平方误差，异常目标可以产生很大的损失并影响拟合。先核对单位、录入与业务原因；若是真实长尾现象，应保留并分析残差、切片及业务损失，而不是删掉使分数不好看的样本。Huber、绝对误差等稳健方法属于后续扩展，本课没有实现或验证。

## 6. 常见错误与下一步

| 错误 | 如何检查与修复 |
|---|---|
| 把多个特征压成一列 | 检查 X.shape；两条样本、两列应为 `[2,2]`，不要将特征当更多样本 |
| 给 Ridge 传负 alpha | alpha 必须非负；本课无惩罚直接用 LinearRegression |
| 先在全表标准化再划分 | 重做划分，把 scaler 放进只在训练数据拟合的 Pipeline |
| 只保存模型系数 | 同时保留预处理状态，否则预测时输入坐标不一致 |
| 认为 alpha 越大测试越好 | 用开发集选定指标比较，保留退步方案，不反复查看 test 调参 |

现在进入下一篇，把缺失值、多列特征、基线和回归树放进同一个公平比较流程。先把本课“改单位为什么影响惩罚”解释清楚，再进入工程代码。

## 继续学习

> [!next] 下一步
> [[01_学习指南/07_传统机器学习与数据分析/逐讲学习/07 公平比较回归模型并检查残差|下一讲：公平比较回归模型并检查残差]]

> [!info]- 练习与记录
> [[01_学习指南/07_传统机器学习与数据分析/示例工程/README#代码导航|查看源码]] · [[01_学习指南/07_传统机器学习与数据分析/示例工程/README#环境与运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 07：传统机器学习与数据分析|本单元完成清单]]
