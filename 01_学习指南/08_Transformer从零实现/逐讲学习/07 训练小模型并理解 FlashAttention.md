---
title: 第 7 讲：训练小模型并理解 FlashAttention
tags:
  - transformer
  - flash-attention
  - pytorch
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 7 讲：训练小模型并理解 FlashAttention

> [!nav] 页面导航
> [[01_学习指南/08_Transformer从零实现/00 Transformer 从零实现学习地图#学习顺序|单元 08：Transformer 从零实现]] · [[01_学习指南/08_Transformer从零实现/逐讲学习/06 对齐自回归目标与交叉熵|上一讲]] · [[01_学习指南/08_Transformer从零实现/00 Transformer 从零实现学习地图#完成后继续|学完继续]]

## 本讲目标与先修知识

前五讲的注意力、mask、Block、RoPE 和移位目标会在这里连成完整流程。读完后，你能运行 CPU/CUDA 训练，分辨训练损失与验证损失，理解逐 token 生成，并解释 FlashAttention 如何减少显存读写而不减少注意力的主要算术复杂度。

## 先运行一个小实验

在 VS Code 打开 `01_学习指南/08_Transformer从零实现/示例工程/`，从该目录 PowerShell 运行：

```powershell
..\..\..\.venv\Scripts\python.exe train.py --device cuda
..\..\..\.venv\Scripts\python.exe train.py --device cpu
```

第一条指定 CUDA GPU，第二条明确使用 CPU；此示例复用共享环境 PyTorch，不需安装新包。也可运行 `..\..\..\.venv\Scripts\python.exe -m pytest -q` 检查测试。

作者侧一次运行记录：19 项测试通过，CUDA 与 CPU 训练均完成。约 3.06 的初始验证 loss 降到约 1.5～1.7；不同设备和运行轮次会有浮点及随机差异。固定语料极小、重复度高，模型很快记住训练片段，验证 loss 可能反弹，生成的短句也不是语言能力评估。作者结果不代表你已完成练习。

## 训练与生成的流程

训练时调用 `model.train()`，每批依次清梯度、前向计算、交叉熵、反向传播、优化器更新。验证时切换 `model.eval()` 并关闭梯度记录；验证 loss 用来观察对未参与更新窗口的预测情况。字符级小数据集很小，数字仅用于检查端到端链路。

贪心生成每一步取分数最大的 token，追加到上下文，再重复预测。它简单、可解释，但不等于高质量解码。本工程没有 KV Cache，故每次生成都重新计算前缀。

代码入口：[train.py](../示例工程/train.py)；训练循环和生成：[training.py](../示例工程/app/training.py)；模型：[model.py](../示例工程/app/model.py)。

## FlashAttention 优化什么

朴素注意力会显式创建长度 T 的分数矩阵 `[T,T]`。序列长时，这个中间矩阵要反复从高带宽显存（HBM）读写。FlashAttention 的核心不是改变 softmax 注意力定义，而是分块计算：把 Q/K/V 切成能放入片上快速存储的小块，计算局部分数，并维护在线 softmax 的归一化状态，不把完整分数矩阵写回 HBM。

设当前处理一个分数块 S，块最大值为 m，指数和为 l，加权 V 累积为 o。新块到来时用新的最大值 m' 合并旧块与新块：

```text
m' = max(m, block_max)
l' = exp(m - m') * l + sum(exp(block_scores - m'))
o' = exp(m - m') * o + sum(exp(block_scores - m') * block_values)
最终输出 = o' / l'
```

重标定因子使之前累积的量与当前最大值保持同一数值尺度，从而可以稳定地分块累积。FlashAttention 仍需约 O(T²·D) 的注意力计算；主要减少中间数据的显存读写，并通过分块与反向重计算节省存储。论文：[FlashAttention](https://arxiv.org/abs/2205.14135)。

本工程的自定义注意力用于显式学习算法，不是 FlashAttention kernel。PyTorch 的 `torch.nn.functional.scaled_dot_product_attention` 在适合的设备、精度、形状和版本条件下可能选择融合实现，不能从函数名保证一定使用某个 kernel。可查 [PyTorch 2.14 SDPA API](https://docs.pytorch.org/docs/2.14/generated/torch.nn.functional.scaled_dot_product_attention.html)。本机单元36已检查出当前Windows wheel未编入FlashAttention，因此本讲CPU/CUDA小模型训练成功不代表运行了FlashAttention；具体后端检查见 [[01_学习指南/36_长上下文显存与分布式训练/逐讲学习/02 实测长度显存耗时与激活重算|SDPA与实际后端]]。FlashAttention数学上计算同类精确注意力，但浮点运算顺序可导致数值差异，不能据此要求与朴素实现逐位相同。

## 完成本单元的检查

- [ ] 能按顺序说明 attention：点积、缩放、mask、softmax、加权 V。
- [ ] 能给出 Q、分数、logits 和标签的形状。
- [ ] 能用测试解释因果 mask 阻断未来信息。
- [ ] 能画出 Pre-Norm/Post-Norm，并说明两种顺序。
- [ ] 能对长度 4 序列写出移位输入和标签。
- [ ] 能跑一次 CPU 和一次 GPU，并解释二者速度不是本实验结论。
- [ ] 能说清 FlashAttention 减少显存 IO，但仍有二次序列长度的主要计算。

## 常见问题

- CUDA 报不可用：先运行 `train.py --device auto`，再读启动打印的 PyTorch/CUDA/GPU 信息；若无 GPU，CPU 路径仍可学习。
- 训练 loss 降而验证 loss 上升：小语料记忆训练样本的过拟合信号；这不是代码一定错误，检查切分后解释局限。
- 生成内容重复：贪心策略、字符词表和小语料都很有限。
- GPU 短任务没有更快：初始化和 kernel 启动开销较大，不能用这个小模型做性能基准。
- 测试在一台设备通过就以为所有设备都验证：本机作者记录覆盖可用 CPU/CUDA，但你的硬件条件可能不同。

## 练习

### 跟做练习

运行 GPU 与 CPU 命令，分别记录设备名、最终 train/validation loss 和一段生成文本。完成标准：如实记录，允许结果略有差异。

### 独立练习

用两三句话说明 FlashAttention 的 IO 收益与计算复杂度。参考：它分块并维护在线 softmax，避免把完整 `T×T` 分数矩阵反复写入显存；仍需约二次于 T 的注意力计算。

### 迁移练习

若上下文长度从 128 增至 512，解释为什么朴素分数矩阵元素数会变为 16 倍。标准：它按 `T²` 增长，`(512/128)²=16`。

> [!example]- 答案解析：CPU/GPU 记录怎么解释
> 同一模型和数据是为了对照设备路径，不是 benchmark。GPU 的启动和数据传输有固定成本，tiny workload 可能 CPU 更快；可用 GPU 学会设备放置和运行路径，性能结论要用规模适当、重复计时且受控的实验。

## 参考资料

- [Attention Is All You Need（Transformer 原始论文）](https://arxiv.org/abs/1706.03762)
- [FlashAttention 论文](https://arxiv.org/abs/2205.14135)
- [PyTorch 2.14 scaled_dot_product_attention 文档](https://docs.pytorch.org/docs/2.14/generated/torch.nn.functional.scaled_dot_product_attention.html)
- [PyTorch 训练与优化器教程](https://docs.pytorch.org/tutorials/beginner/basics/optimization_tutorial.html)

## 继续学习

> [!next] 下一步
> [[01_学习指南/08_Transformer从零实现/00 Transformer 从零实现学习地图#完成后继续|本单元完成后继续]]

> [!info]- 练习与记录
> [[01_学习指南/08_Transformer从零实现/示例工程/README#代码导航|查看源码]] · [[01_学习指南/08_Transformer从零实现/示例工程/README#环境与运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 08：Transformer 从零实现|本单元完成清单]]
