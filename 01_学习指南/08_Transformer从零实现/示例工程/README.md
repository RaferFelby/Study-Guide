---
title: 单元 08 示例工程：Transformer 从零实现
tags:
  - example
  - transformer
  - pytorch
status: published
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# 单元 08 示例工程：Transformer 从零实现

> [!nav] 页面导航
> [[01_学习指南/08_Transformer从零实现/00 Transformer 从零实现学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/08_Transformer从零实现/逐讲学习/01 看懂缩放点积注意力|从第一讲开始：看懂缩放点积注意力]]

这个小型工程用 PyTorch 手写缩放点积注意力、因果/padding mask、RoPE、多头注意力和 Transformer Block，再训练字符级 decoder-only 模型预测下一个字符。固定本地语料，不下载数据；目的在于看懂计算流程，不代表模型具备真实语言能力。

## 环境与运行

工程使用工作区共享 `.venv`，不需要新增依赖。已验证 PyTorch 2.14.0+cu130、Python 3.13.12，以及 NVIDIA RTX 5070 Laptop GPU 的 CUDA 路径。设备由参数选择：

```powershell
..\..\..\.venv\Scripts\python.exe train.py --device cuda
..\..\..\.venv\Scripts\python.exe train.py --device cpu
```

默认 `--device auto` 会在 CUDA 可用时选 GPU，否则选 CPU。其他参数：`--epochs` 训练轮数，`--batch-size` 每批样本窗口数，`--context-length` 每个输入上下文长度。模型很小，GPU 启动/内核开销可能让一次短训练看起来不比 CPU 快；本练习优先验证设备可用和概念正确，不作为硬件性能基准。

运行测试：

```powershell
..\..\..\.venv\Scripts\python.exe -m pytest -q
```

## 代码导航

- [app/attention.py](./app/attention.py)：RoPE 旋转、缩放点积注意力、因果与有效 token mask、多头自注意力。
- [app/model.py](./app/model.py)：Pre-Norm/Post-Norm Transformer Block 与 decoder-only 语言模型。
- [app/data.py](./app/data.py)：本地字符词表、固定文本、错一位的输入/目标窗口和 DataLoader。
- [app/training.py](./app/training.py)：忽略 padding 目标的 token 交叉熵、训练、验证和贪心逐 token 生成。
- [train.py](./train.py)：参数解析、自动/指定设备选择、训练和生成入口。
- [tests/test_attention.py](./tests/test_attention.py)：注意力形状、未来泄漏、padding mask、RoPE 和失败输入。
- [tests/test_model.py](./tests/test_model.py)：两种 Norm、logits 形状、梯度和未来信息隔离。
- [tests/test_data_and_training.py](./tests/test_data_and_training.py)：标签移位、padding loss 与训练/验证路径。

- [block_parts_demo.py](./block_parts_demo.py)：CPU 手算版 LayerNorm、固定 ReLU FFN 与严格同形残差；没有替换 app/model.py 的 GELU。
- [test_block_parts.py](./tests/test_block_parts.py)：数值和梯度、常量输入、非法 epsilon、位置隔离、仿射参数和 Pre/Post-Norm 顺序。

先按 [[01_学习指南/08_Transformer从零实现/逐讲学习/03 手算归一化前馈网络与残差|部件详细课]]运行 `..\..\..\.venv\Scripts\python.exe block_parts_demo.py`；这一小实验固定 CPU，不需要 GPU 训练。

## 边界

注意力分数矩阵形状约为 `[batch, heads, sequence, sequence]`，序列变长时会迅速占用更多内存。手写注意力在 float32 中清楚呈现分数、mask 和 softmax，不是高性能 FlashAttention 实现。生产环境可在理解概念后评估 `torch.nn.functional.scaled_dot_product_attention`；实际使用哪个融合内核取决于 PyTorch 版本、设备、数据类型、形状和调用条件。

字符级词表和重复短句极小，训练容易记住样例，输出句子不能证明语言建模能力。此示例没有实现 KV Cache、混合精度、训练检查点或 Encoder-Decoder。
