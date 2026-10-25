---
title: 单元 09 示例工程：大模型架构与资源估算
tags:
  - example
  - llm-architecture
  - python
status: published
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# 单元 09 示例工程：大模型架构与资源估算

> [!nav] 页面导航
> [[01_学习指南/09_主流大模型架构与参数估算/00 主流大模型架构与参数估算学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/09_主流大模型架构与参数估算/逐讲学习/01 从 Transformer 配置读懂模型骨架|从第一讲开始：从 Transformer 配置读懂模型骨架]]

这个小工程读取两份经过核对的模型结构参数，用 Python 标准库估算稠密 Decoder Transformer 的参数量和普通 KV Cache 大小。它不下载模型、不执行推理，也不需要安装任何依赖。

## 运行方式

在 VS Code 打开本目录的终端，从示例工程目录运行：

```powershell
..\..\..\.venv\Scripts\python.exe estimate.py configs\qwen2_5_7b.json --batch-size 4 --sequence-length 8192
..\..\..\.venv\Scripts\python.exe estimate.py configs\llama3_1_8b.json --batch-size 4 --sequence-length 8192
..\..\..\.venv\Scripts\python.exe -m pytest -q
```

参数量估算使用配置文件中的结构数字；KV Cache 默认按 BF16 每元素 2 字节计算，可用 `--dtype float32` 改为 4 字节。输出的 GiB 以 \(2^{30}\) 字节为单位。

## 代码导航

- [estimate.py](./estimate.py)：读取配置、估算稠密模型参数数目、权重存储和普通 KV Cache。
- [configs/qwen2_5_7b.json](./configs/qwen2_5_7b.json)：Qwen2.5-7B 的结构字段快照；出处和限制见文件内说明。
- [configs/llama3_1_8b.json](./configs/llama3_1_8b.json)：Llama 3.1-8B 的结构字段快照；出处和限制见文件内说明。
- [tests/test_estimate.py](./tests/test_estimate.py)：用小型人工配置验证参数公式、缓存公式和无效输入。

## 估算边界

该计算器针对 RoPE、稠密 SwiGLU MLP、标准 MHA/GQA 投影、无投影 bias 的 Decoder-only 模型；它按配置里的词表 embedding、输出头是否共享来估算。与真实权重文件的小差异可能来自配置取整、实现细节或额外模块。

它不直接估算 MoE、MLA、量化元数据、训练激活、CUDA kernel workspace、碎片和并行切分。MoE 的“总参数”和“每 token 激活参数”要分别统计；MLA 的缓存结构也不是这里的 K/V 张量公式。资源估算用于初筛，不等于运行保证。
