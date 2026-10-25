---
title: 单元 08 参考工程验证记录
tags:
  - transformer
  - verification
  - author-record
status: published
updated: 2026-10-23
cssclasses: ["guide-page", "guide-reference"]
---

# 单元 08 参考工程验证记录

> [!tip] 导航
> [[01_学习指南/08_Transformer从零实现/00 Transformer 从零实现学习地图|单元 08：Transformer 从零实现]] · [[01_学习指南/08_Transformer从零实现/示例工程/README|示例工程代码导航]]

本页记录作者运行环境、测试和示例结果；不代表学习者已完成章节或掌握概念。


## 注意力操作与基础部件（2026-10-23，本轮）

本轮更新 [[01_学习指南/08_Transformer从零实现/逐讲学习/01 看懂缩放点积注意力|注意力第 1 讲]]及 [[01_学习指南/08_Transformer从零实现/逐讲学习/03 手算归一化前馈网络与残差|基础部件详细课]]。第 1 讲新增完整 Q/K/V 数值调用，明确 is_causal=False 对应无 mask 例子。补充课增加 Embedding 查表与重复 ID 梯度、LayerNorm 的轴／eps／仿射参数、固定 ReLU FFN、GELU 区别、残差和 Pre/Post-Norm。新测试覆盖梯度、低精度拒绝、统计溢出、位置隔离与错误 ID；原模型源码未替换。

- 在根共享 Python 3.13.12 下运行，本单元全部 **44 项测试通过**。新增源码／测试通过 Ruff 静态与格式检查。
- 本轮六单元合计 232 项测试；教材验证脚本最终完成 45 次独立进程调用，其中两次是预期的拒绝覆盖／回填失败，其余正常完成。本文只引用本单元对应记录，不把其他单元结果算成本单元测试。
- 共 29 段本轮教材 Python 片段经过 Ruff 格式整理，27 段完整脚本或定义片段通过静态检查与独立执行；2 段明确标注为函数内部的核心片段未作为独立脚本运行，行为由完整示例及测试检查。

检查证据：`.author-tools/hour-check-block-e316d03a2dd54b2a9df99794cc4f51fa.json`；教材独立调用、实际输出与数据库摘要保存在 `.author-tools/hour-20261023-0fb9922b9fbc486db7a13e97c7d69269/commands.json` 和 `summary.json`。作者工具的首次抽取把窗口内部片段当独立脚本导致 NameError，调整抽取范围后重跑；不是把该次失败记为成功。诊断工具首次处理超时输出时误判 str／bytes，修正后才取得堆栈证据。

范围限制：实际 PyTorch 2.14.0+cu130、CUDA 可用；全单元测试包含既有 CPU／CUDA 参数化路径，新手算脚本固定 CPU。首轮 pytest 缓存目录写入警告后，复跑使用 -p no:cacheprovider，仅关闭缓存插件，没有跳过测试。未重新训练完整语言模型或做性能基准；手算 LayerNorm 不宣称复制低精度内核行为。 无依赖安装／升级，没有调用真实模型，也未完成 Obsidian 阅读视图的视觉验收。学习者完成标记没有自动勾选。以下保留原有历史记录。

## 环境

| 项目 | 实际环境 |
|---|---|
| 操作系统 | Windows |
| Python | 3.13.12 |
| PyTorch | 2.14.0+cu130 |
| CUDA build | 13.0 |
| CUDA 可用性 | True |
| GPU | NVIDIA GeForce RTX 5070 Laptop GPU（约 8 GB 显存） |
| 新增依赖 | 无；复用共享环境 |

## 作者验证结果

- `pip check`：`No broken requirements found.`
- Ruff lint：通过；Ruff format 检查：通过。
- Python 语法检查：通过。
- 示例工程 pytest：19 passed，覆盖 CPU 和可用 CUDA 路径。
- `train.py --device cuda`：完成 8 轮训练与贪心生成，设备确认是 RTX 5070 Laptop GPU。
- `train.py --device cpu`：完成同一训练闭环。
- 第 4 讲结构/位置组件与注意力形状、因果 mask、padding mask、梯度路径均由测试覆盖。

## 一次示例输出摘要

本次 CUDA 运行的字符词表大小为 18，训练窗口 1271 个，验证窗口 215 个。训练 loss 从约 1.030 降到 0.187；验证 loss 初始约 3.063，随后降至约 1.545（中途有波动）。CPU 数值接近但不完全相同。小语料在训练集上很快过拟合，正好说明训练 loss 下降不等于验证表现改善；本数字仅对应这份重复合成语料、固定参数与当前版本，不作为模型质量基准。

## 限制

手写注意力采用显式分数矩阵与 float32 softmax，目的是教学可读性；不等同于 FlashAttention，也不用于比较 GPU 性能。GPU 上一轮小 batch 任务的 kernel 启动开销可能占主导。测试证明当前输入形状、mask 和梯度约束满足预期，不证明所有长度、精度与硬件均无数值风险。

下次改变模型、mask 或 PyTorch 版本后，重新记录依赖、设备与实际测试输出。不要把小型字符样例生成了可读句子描述成真实语言能力。
