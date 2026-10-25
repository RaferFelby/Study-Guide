---
title: 第 6 讲：检查点续训与EarlyStopping
aliases:
  - checkpoint续训早停
tags:
  - pytorch
  - checkpoint
  - early-stopping
  - reproducibility
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 6 讲：检查点续训与EarlyStopping

> [!nav] 页面导航
> [[01_学习指南/06_PyTorch训练闭环/00 PyTorch训练闭环学习地图#学习顺序|单元 06：PyTorch训练闭环]] · [[01_学习指南/06_PyTorch训练闭环/逐讲学习/05 训练验证与指标记录|上一讲]] · [[01_学习指南/06_PyTorch训练闭环/逐讲学习/07 训练故障排查|下一讲]]

## 这一讲要解决什么问题

训练可能被中断，验证集最好的模型也可能不是最后一个模型。检查点保存的是“继续做同一实验所需的状态”，Early Stopping 用验证指标决定何时停止。检查点可以独立支持续训；保存验证集最佳状态也不要求启用早停。本工程组合两者，演示恢复状态、最佳模型选择与停止策略的不同职责。

## 检查点应该保存什么

至少保存：

- model.state_dict：模型参数和需要持久保存的缓冲；缓冲是模型中不作为可训练参数但需要保留的状态，例如某些归一化层的运行统计。本例两层回归器没有这些额外统计，不能因此认为所有模型都只存参数；
- optimizer.state_dict：动量、二阶统计等优化器状态；
- scheduler.state_dict：学习率调度状态；
- 当前 epoch、最佳验证指标和早停计数；
- 随机数生成器状态、训练配置和数据划分设置；启用 AMP 时还要保存梯度缩放器状态。

只保存模型权重可以用于推理，但不足以保证从中断处连续续训。保存 checkpoint 时使用临时文件写完再替换目标文件，是生产环境中减少半写入文件风险的一种办法。

### 本示例恢复随机性的范围

示例工程保存并恢复 PyTorch 的 CPU 随机状态和当前可见的全部 CUDA 设备随机状态。示例数据和训练/验证切分使用带固定 seed 的 PyTorch 局部生成器，数据加载器使用默认 `num_workers=0`；这足以演示本工程的 epoch 边界续训流程。它没有保存 Python `random`、NumPy 或多 worker 数据增强的随机状态，因为示例训练流程没有使用这些随机来源。

因此，本例的“续训”指在兼容的配置和设备数量下恢复模型、优化器、调度器、早停器、梯度缩放器、训练轮次、历史记录以及 PyTorch 随机状态；它不是跨 PyTorch 版本、不同 GPU 或任意数据管道都逐位一致的保证。真实工程新增任何随机来源或 worker 后，都要把相应状态纳入检查点，并通过中断前后对照实验验证恢复效果。

## best 和 last 的区别

- last.pt 表示最近一次保存的训练状态，用于中断后继续。
- best.pt 表示按本工程显著改善规则接受的最佳状态，可作为独立评估或部署的候选。实现要求新损失严格小于此前接受的最好值减去 `min_delta=1e-5`；微小下降不一定更新，所以文件不保证对应日志数值最低的一轮。这是工程选择，保存数值最小状态与早停计数也可以分别设计。

如果验证 loss 越小越好，改善条件是 current < best - min_delta；如果指标越大越好，比较方向要反过来。不要把最后一个 epoch 自动当成最佳模型。

## Early Stopping

Early Stopping 在连续 patience 个 epoch 没有达到最小改善时停止。它不是证明模型已经达到全局最优，而是一个计算预算和过拟合风险控制策略。patience 太小可能过早停止，太大则浪费计算。

示例工程的 EarlyStopping 只负责比较指标和维护状态，保存文件由训练流程完成；职责分开后更容易测试和替换。

## 断点续训流程

1. 启动时读取配置和 checkpoint 路径，并确认影响数据、优化器和设备的配置与保存时一致。
2. 创建同样结构的模型、优化器和调度器。
3. 加载三者 state_dict、梯度缩放器、早停状态、随机状态，以及 epoch 和 history。
4. 检查设备数量和训练配置与 checkpoint 相符；配置不匹配时创建新实验，不要悄悄续训。
5. 从保存的下一个 epoch 继续，追加日志而不是覆盖。

如果改了模型结构、数据划分、优化设置或损失定义，不应把它当作同一实验直接续训；示例会拒绝关键训练配置不一致的 checkpoint。增加 `--epochs` 上限可以继续训练；改变随机种子、batch 大小、学习率、裁剪阈值、AMP 或设备则应另开实验。

## 动手操作

1. 运行训练到第 5 个 epoch，检查 results/last.pt 和 results/best.pt。
2. 用 --resume results/last.pt 继续训练，比较 history 是否接续。
3. 人为缩短 patience，观察训练是否早于最大 epoch 结束。
4. 删除或改名 checkpoint，练习根据错误信息定位路径、结构或版本问题。

## 常见错误

- 只保存 model.state_dict，却声称可以精确断点续训。
- 恢复模型后忘记恢复 optimizer，导致学习率状态和动量重置。
- 把 best checkpoint 覆盖成 last，最后无法回到验证集最佳状态。
- 继续训练时更换数据划分，却不更新实验名称和记录。

## 练习与答案解析

### 跟做练习：设计 checkpoint 字段

写出一个最小 checkpoint 字典，包含模型、优化器、epoch、最佳验证 loss 和历史记录。

> [!example]- 参考答案
> 本工程的 checkpoint 包含 model_state_dict、optimizer_state_dict、scheduler_state_dict、epoch、history、early_stopping（含 best 与 bad_epochs）、scaler_state_dict、training_config 和 CPU/CUDA 随机数状态。字段名稳定；恢复时还会校验训练配置与 CUDA 设备数量。

### 独立练习

给 EarlyStopping 增加 mode 参数，支持 min 和 max。分别测试连续变差、恰好达到 min_delta 和重新改善的情况。

### 迁移练习

设计多次实验的目录结构，要求能区分数据版本、模型配置、随机种子和运行时间；说明为什么不要把所有结果都写进一个 history.json。

## 本讲小结

last 用于恢复，best 用于选择。断点续训保存的不只是参数，还包括优化器、调度器、计数和实验上下文；改变实验条件时必须重新编号和记录。

## 继续学习

> [!next] 下一步
> [[01_学习指南/06_PyTorch训练闭环/逐讲学习/07 训练故障排查|下一讲：训练故障排查]]

> [!info]- 练习与记录
> [[01_学习指南/06_PyTorch训练闭环/示例工程/README#代码导航|查看源码]] · [[01_学习指南/06_PyTorch训练闭环/示例工程/README#运行训练|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 06：PyTorch 与训练闭环|本单元完成清单]]
