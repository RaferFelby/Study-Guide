---
title: 单元 06 示例工程：PyTorch 训练闭环
tags:
  - example
  - pytorch
  - training
  - checkpoint
status: published
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# 单元 06 示例工程：PyTorch 训练闭环

> [!nav] 页面导航
> [[01_学习指南/06_PyTorch训练闭环/00 PyTorch训练闭环学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/06_PyTorch训练闭环/逐讲学习/01 Tensor设备与广播|从第一讲开始：Tensor设备与广播]]

这是单元 06 的最小训练工程：用一个两层回归网络学习带噪声的二次函数，同时记录训练/验证 loss、学习率、梯度范数、吞吐量和设备信息。工程还包含 best/last checkpoint、断点续训、Early Stopping 和受控故障注入。

## 准备环境

先按仓库根目录 [README](../../../90_参考与维护/01 使用与环境/01 共享Python环境与运行约定.md#共享-python-环境) 创建并安装共享环境。运行训练前，在本目录终端确认共享解释器能导入 PyTorch：

~~~powershell
..\..\..\.venv\Scripts\python.exe -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
~~~

若缺少 PyTorch，请先按根目录说明选择 CPU 或 CUDA wheel；不要在本单元另建虚拟环境。命令最后输出 True 表示 PyTorch 可用 CUDA，输出 False 时仍可使用 CPU 运行示例。

## 运行训练

[[01_学习指南/06_PyTorch训练闭环/逐讲学习/05 训练验证与指标记录|第 5 讲：训练验证与指标记录]]补充 `lesson_04_average.py`、`lesson_04_loop.py` 和召回率练习，先核对加权损失与轮末重测，再启动完整训练；[[01_学习指南/06_PyTorch训练闭环/逐讲学习/07 训练故障排查|第 7 讲：训练故障排查]]补充 `lesson_06_inspect.py`，依次观察正常、NaN、空张量与全非有限值，再运行故障与修复对照。这些课堂脚本由学习者按正文创建，配套函数已放在 `app/diagnostics.py`。

学习数据加载时，先按 [[01_学习指南/06_PyTorch训练闭环/逐讲学习/02 Dataset与DataLoader|第 2 讲：Dataset与DataLoader]] 创建 `dataset_demo.py` 和划分／顺序／批次检查小脚本，再按 [[01_学习指南/06_PyTorch训练闭环/逐讲学习/03 拼齐变长序列并验证掩码|变长详细课]] 创建调用脚本。配套 `app/batching.py` 处理右侧补齐，mask 的 True 表示有效位置；全部先在 CPU 当前进程运行。课堂代码由学习者创建，源码导航列出预先存在的实现与测试。

若第一次学习，先按 [[01_学习指南/06_PyTorch训练闭环/逐讲学习/04 Module优化器与调度器|第 4 讲：Module优化器与调度器]] 在本目录创建 `lesson_03_model.py`、`lesson_03_update.py`、`lesson_03_decay.py`、`lesson_03_schedule.py`，用共享解释器分别运行。预期为 49 个参数、单步权重 0.4 与损失 2.56、衰减后 0.98、四行学习率；练习文件也在正文提供。它们由学习者创建，不属于预先存在的源码导航条目。小实验使用 CPU，无需训练输出目录或网络。

~~~powershell
..\..\..\.venv\Scripts\python.exe train.py --epochs 30 --output-dir results
~~~

训练完成后检查：

- results/history.json：每个 epoch 的 loss、学习率、梯度范数、吞吐量和显存字段；
- results/best.pt：按 `min_delta=1e-5` 显著改善规则接受的最佳状态，微小下降不一定更新；
- results/last.pt：最近一次状态，可用于续训。

断点续训：

~~~powershell
..\..\..\.venv\Scripts\python.exe train.py --epochs 50 --resume results/last.pt --output-dir results
~~~

受控故障：

~~~powershell
..\..\..\.venv\Scripts\python.exe train.py --overfit-small --epochs 30 --output-dir results/overfit
..\..\..\.venv\Scripts\python.exe train.py --learning-rate 2.0 --epochs 5 --output-dir results/large-lr
..\..\..\.venv\Scripts\python.exe train.py --inject-nan --epochs 5 --output-dir results/nan
~~~

故障实验的目标是验证检查和记录路径，不是追求成功训练。注入 NaN 时程序应清晰报告批次位置并停止。

## 代码导航

- [app/data.py](./app/data.py)：固定随机种子、数据集、划分和 DataLoader。
- [batching.py](./app/batching.py)：变长整数列表右侧补齐，返回 CPU 值、长度和有效掩码；空批次拒绝，批次内空序列允许。
- [diagnostics.py](./app/diagnostics.py)：按实际分母汇总批次损失、只读观察稠密实数张量的非有限值与有限极值。
- [app/model.py](./app/model.py)：两层回归模型和参数统计。
- [app/training.py](./app/training.py)：训练、验证、指标、梯度裁剪、检查点和 Early Stopping。
- [train.py](./train.py)：命令行入口与故障注入。
- [tests/test_training.py](./tests/test_training.py)：模型输出、数据划分、检查点和训练组件测试。
- [test_batching.py](./tests/test_batching.py)：真实零、空序列、整型边界、错误输入、DataLoader 接入和小规模重构检查。
- [test_metrics.py](./tests/test_metrics.py)：损失分母、末批、多输出、验证模式与梯度记录、观察器、空输入、形状不匹配和 NaN 批次定位。

2026-10-14 新增 epoch 边界续训对照：在同一 CPU 环境比较连续 4 轮与先 2 轮再恢复到 4 轮的模型、优化器、调度器、早停、随机状态和损失。运行 `..\..\..\.venv\Scripts\python.exe -m pytest -q tests` 执行全套测试；2026-10-23 增加 10 项指标与诊断测试后，共有 23 项。`unittest discover` 可运行其中 22 项，独立的 pytest 续训函数需 pytest 执行。该 CPU 对照不能扩展为跨设备或版本的逐位恢复承诺。若 pytest 无法创建系统临时目录，可用 `--basetemp` 指定工作区内一个尚不存在的独立临时路径；该选项会清理目标路径，不能指向结果或源码目录。

训练和验证现在统一报告按输出元素平均的 MSE；原 `[B, 1]` 示例定义不变，多输出回归也保持一致。拒绝空批次及预测／目标形状不一致；NaN 注入错误附训练批次编号。旧结果按当时代码和形状理解，不修改历史日志。

## 设计边界

示例使用 CPU 也能运行，但不代表真实 GPU 训练的吞吐量或显存结果。数据是合成数据，模型只是教学用两层网络；它不能证明真实任务效果。实验记录应保留 Python、PyTorch、设备、随机种子、配置和数据生成方式。
