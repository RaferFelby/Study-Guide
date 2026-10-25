---
title: 第 2 讲：估算参数量并读懂 SwiGLU 与 RMSNorm
tags:
  - llm-architecture
  - parameter-count
  - swiglu
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 2 讲：估算参数量并读懂 SwiGLU 与 RMSNorm

> [!nav] 页面导航
> [[01_学习指南/09_主流大模型架构与参数估算/00 主流大模型架构与参数估算学习地图#学习顺序|单元 09：主流大模型架构与参数估算]] · [[01_学习指南/09_主流大模型架构与参数估算/逐讲学习/01 从 Transformer 配置读懂模型骨架|上一讲]] · [[01_学习指南/09_主流大模型架构与参数估算/逐讲学习/03 用 GQA 与 KV Cache 估算推理显存|下一讲]]

## 本讲目标与先修知识

需要矩阵形状和“一个权重就是一个可学习数字”的直觉，见 [[01_学习指南/05_数学概率与优化/逐讲学习/01 向量矩阵与张量形状|向量与矩阵]]。本讲先算 embedding，再算注意力、SwiGLU FFN 和 Norm，最后用脚本合计两个模型。

## 矩阵参数怎样数

一个输入宽度 a、输出宽度 b 的线性层，权重形状为 [b,a]，参数个数是 a×b。若有 bias，还加 b 个偏置。模型配置常关闭这些线性层 bias，因此先按无 bias 算，再按具体设置补充。

词嵌入表形状为 [V,D]，有 V×D 个参数。若输出 LM Head 与输入 embedding 共享权重，不能重复计数；若不共享，输出投影再增加 V×D 个参数。

## SwiGLU 的三个矩阵

SwiGLU 是门控前馈网络。它从输入 x 并行得到 gate 和 up 两个中间向量，把 gate 经过 SiLU 后逐元素乘 up，再通过 down 投影回原宽度：

~~~text
gate = SiLU(x W_gate)
up   = x W_up
hidden = gate ⊙ up
output = hidden W_down
~~~

若隐藏宽度 D、中间宽度 F，无 bias 时三个矩阵合计约 3×D×F。普通两层 MLP 约为 2×D×F，所以相同 D、F 下 SwiGLU 参数更多；模型通常会相应选择 F。

## 注意力和 RMSNorm 的参数

采用 GQA 时，Query 投影 D→D，输出投影 D→D；Key 和 Value 投到 Hkv×head_dim。每层注意力矩阵参数为：

~~~text
2D² + 2D(Hkv × head_dim)
~~~

RMSNorm（均方根归一化）计算每个 token 特征的均方根并用可学习 scale 调整；常见形式有一组 D 维 scale，不做均值中心化，也通常没有 bias。一层按注意力前和 FFN 前两个 RMSNorm 计 2D；L 层后再加末尾 D。

## 把各项加起来

忽略 RoPE（没有可学习位置表）、量化元数据等时：

~~~text
Attention = L × (2D² + 2D × Hkv × head_dim)
SwiGLU   = L × 3DF
Norm     = (2L + 1)D
Embedding/output = V×D + (未共享时再加 V×D)
~~~

将这些加总得到 Dense 参数估计。容易漏掉每层都重复一次的 L，也容易将共享输出头算两遍。

## 运行估算器

在示例工程目录运行：

~~~powershell
..\..\..\.venv\Scripts\python.exe estimate.py configs\qwen2_5_7b.json
..\..\..\.venv\Scripts\python.exe estimate.py configs\llama3_1_8b.json
~~~

脚本读取 JSON，检查维度，计算投影矩阵并合计参数。没有联网步骤，也不导入第三方包。

当前公式对两份快照的结果约为 Qwen2.5-7B 7.615B、Llama 3.1-8B 8.030B。估算含两个词表矩阵，按零 bias 假设；标签是约数，差异也可能来自额外归一化或实现细节。参数文件与公式见 [估算器](../示例工程/estimate.py)。

## 常见错误与练习

- 把矩阵参数算成 a+b：应为 a×b。
- 忘记层数：每层投影参数乘 L。
- 把 SwiGLU 当两矩阵 MLP：gate/up/down 有三组矩阵。
- 忘记 embedding 和 LM Head：词表大时两张 [V,D] 矩阵很可观。
- 参数量不等于显存：权重只是其中一项。

### 跟做练习

D=8、F=16、L=2，算 SwiGLU 权重数。答案：每层 3×8×16=384，两层共 768。

### 独立练习

V=1000、D=64，输入 embedding 有多少参数？输出头不共享时再增加多少？答案：各 64,000，合计 128,000。

### 迁移练习

用估算器检查一份 Dense 官方配置，指出最大的两个参数组成项。完成标准：列出字段、公式、embedding 是否共享及未计项目。

> [!example]- 答案解析：GQA 注意力项
> Q 和输出投影宽度仍为 D，因此两项合计 2D²。只有 K、V 输出宽度变成 Hkv×head_dim，合计 2D×Hkv×head_dim。不能把所有投影都误算成 D×D。

## 继续学习

> [!next] 下一步
> [[01_学习指南/09_主流大模型架构与参数估算/逐讲学习/03 用 GQA 与 KV Cache 估算推理显存|下一讲：用 GQA 与 KV Cache 估算推理显存]]

> [!info]- 练习与记录
> [[01_学习指南/09_主流大模型架构与参数估算/示例工程/README#代码导航|查看源码]] · [[01_学习指南/09_主流大模型架构与参数估算/示例工程/README#运行方式|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 09：主流大模型架构与参数估算|本单元完成清单]]
