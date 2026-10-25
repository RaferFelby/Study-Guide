---
title: 单元 07 示例工程：传统机器学习与数据分析
tags:
  - example
  - machine-learning
  - scikit-learn
status: published
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# 单元 07 示例工程：传统机器学习与数据分析

> [!nav] 页面导航
> [[01_学习指南/07_传统机器学习与数据分析/00 传统机器学习与数据分析学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/07_传统机器学习与数据分析/逐讲学习/01 用 pandas 看懂一张数据表|从第一讲开始：用 pandas 看懂一张数据表]]

该工程用固定随机种子生成一份合成客户续费表格，比较多数类基线、逻辑回归、决策树、随机森林和梯度提升。数据无需下载；输出只用于学习流程，不代表真实业务。作者实际验证的 Python/NumPy/pandas/scikit-learn/SciPy 版本和指标见 [参考验证记录](../../../90_参考与维护/单元验证/07 传统机器学习与数据分析验证记录.md)。

## 环境与运行

本机使用仓库根目录的共享 `.venv`。本单元要求 NumPy、pandas 与 scikit-learn；单元最小依赖写在 [requirements.txt](./requirements.txt)，工作区约束见 [根目录机器学习依赖清单](../../../requirements-ml.txt)。安装依赖需遵守根目录 `AGENTS.md` 的审批规则。2026-10-14实际导入版本：Python3.13.12、NumPy2.5.3、pandas3.0.6、scikit-learn1.9.1；较早实验环境保留在原验证记录中。

在本工程目录的 VS Code PowerShell 终端运行：

```powershell
..\..\..\.venv\Scripts\python.exe train.py
```

相对路径从工程目录计算：依次返回 `07_传统机器学习与数据分析`、`01_学习指南`、仓库根目录，再进入 `.venv\Scripts`。程序写出：

- `results/synthetic_customers.csv`：这次运行所用的固定合成表格；
- `results/report.json`：数据划分、开发集候选模型分数、最终模型、dev 阈值和测试集指标。

输出数值应在相同依赖版本与随机种子下保持稳定。不同依赖版本可能造成极小的浮点或模型实现差异；报告需保留实际环境版本。

需要保留旧报告时，使用`..\..\..\.venv\Scripts\python.exe train.py --output-dir results-my-ap-01`指定自己的新目录；默认`results`仍保持旧接口，会覆盖其中同名报告。不要覆盖作者验证目录。

## 代码导航

- [app/data.py](./app/data.py)：确定性生成数值/类别特征、目标和少量缺失值。
- [app/modeling.py](./app/modeling.py)：数据切分、缺失值填补、标准化、独热编码与候选分类器 Pipeline。
- [app/evaluation.py](./app/evaluation.py)：分类指标与仅基于开发集选择 F1 阈值。
- [train.py](./train.py)：运行训练、开发集比较、阈值选择、一次性测试评估并保存 JSON 报告。
- [test_metrics.py](./test_metrics.py)：AP与梯形面积的差异、阈值反例和失败输入回归。

- [regression_demo.py](./regression_demo.py)：独立的一维线性回归、训练均值基线、MAE／MSE／RMSE／R²；只打印合成结果。
- [test_regression.py](./test_regression.py)：手算、留出目标不影响拟合、常量目标、单位变化和输入错误。
- [calibration_demo.py](./calibration_demo.py)：独立的可靠性表、Brier／ECE、固定逻辑回归与留出 sigmoid 校准；只打印结果。
- [test_calibration.py](./test_calibration.py)：手算、端点、空箱、样本数权重、ECE 反例、冻结预处理／分类器、数据边界和失败输入。
- [regression_comparison.py](./regression_comparison.py)：独立合成耗时数据、中位数填补／标准化、五个回归候选、开发集选优与残差。
- [test_regression_comparison.py](./test_regression_comparison.py)：Ridge／回归树手算、单位、划分、训练统计、留出标签隔离及失败输入。

回归补充课在本目录运行 `..\..\..\.venv\Scripts\python.exe regression_demo.py`；针对本课检查使用 `..\..\..\.venv\Scripts\python.exe -m pytest test_regression.py -q`。详见 [[01_学习指南/07_传统机器学习与数据分析/逐讲学习/03 拟合一条直线并读懂回归指标|完整操作与答案]]；原分类训练入口与输出文件保持独立。

## 回归比较补充实验

回归分支先从 [[01_学习指南/07_传统机器学习与数据分析/逐讲学习/06 从多特征回归理解Ridge与标准化|Ridge 与标准化]]进入，再读 [[01_学习指南/07_传统机器学习与数据分析/逐讲学习/07 公平比较回归模型并检查残差|公平比较回归模型]]。在本目录运行 `..\..\..\.venv\Scripts\python.exe regression_comparison.py`；检查使用 `..\..\..\.venv\Scripts\python.exe -m pytest test_regression_comparison.py -q`。300 条合成文档耗时按 180／60／60 划分，固定开发 RMSE 选择模型，再比较选中模型与训练均值基线的 test 结果。脚本只打印，不保存模型或改写原分类报告。本次选择 linear，数值和限制见完整教程。

## 概率校准补充实验

先完成 [[01_学习指南/07_传统机器学习与数据分析/逐讲学习/09 手算概率误差与可靠性表|手算与可靠性坐标]]，再按 [[01_学习指南/07_传统机器学习与数据分析/逐讲学习/10 隔离校准数据并检查校准是否改善|完整校准教程]]运行：

```powershell
..\..\..\.venv\Scripts\python.exe calibration_demo.py
..\..\..\.venv\Scripts\python.exe -m pytest test_calibration.py -q
```

固定三份数据为训练 720、校准 240、测试 240。复用的 `x_dev/y_dev` 在此实验专用于校准，不执行原 train.py 的模型选择。冻结整个 Pipeline，用 `FrozenEstimator` 包装已拟合模型。默认方法 sigmoid；本次合成测试上 Brier 从 0.181333 变为 0.186542，未改善。保留这次观察，不以测试分数反复选择校准方法。脚本不保存模型或报告，不依赖绘图库，完整命令仅打印结果。

本补充实测 sklearn 1.9.1，既有依赖声明不等于各版本数值均相同。导入 `calibration_demo` 不会训练或打印；函数调用后才执行相应拟合。与原分类入口的模型比较报告相互独立。

## 指标名称勘误与验证

本工程计算的是平均精确率AP。当前报告使用`average_precision`和`selected_model_by_dev_average_precision`；旧`pr_auc`和`selected_model_by_dev_pr_auc`保留为兼容字段，实际含义仍是AP，`metric_definitions`写明此区别。旧报告数值不变，但不能将其解释为梯形PR曲线面积。

在本目录执行`..\..\..\.venv\Scripts\python.exe -m pytest -q test_metrics.py`验证。终端现在显示dev AP；原历史记录中AP的标签勘误另记在作者验证页。

## 数据与设计边界

续费目标由一条预先写明的合成概率公式生成。因此模型分数只说明代码流程可运行，不能外推到真实客户、收益、群体公平或部署效果。示例按行随机分层切分；真实数据若包含重复用户或时间依赖，应采用分组/时间切分并保持独立测试集。

## 作者验证状态

作者已在 Python 3.13.12、NumPy 2.5.3、pandas 3.0.6、scikit-learn 1.9.1 与 SciPy 1.18.1 的共享环境运行示例，并完成依赖兼容检查。具体结果与局限见参考验证记录。宽泛版本范围并不表示所有版本组合均已逐一验证。
