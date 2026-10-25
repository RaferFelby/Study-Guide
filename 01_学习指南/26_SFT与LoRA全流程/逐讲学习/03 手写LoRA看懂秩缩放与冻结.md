---
title: 第 3 讲：手写LoRA看懂秩缩放与冻结
tags: [learning, pytorch, sft, lora]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 3 讲：手写LoRA看懂秩缩放与冻结

> [!nav] 页面导航
> [[01_学习指南/26_SFT与LoRA全流程/00 SFT与LoRA全流程学习地图#学习顺序|单元 26：SFT与LoRA全流程]] · [[01_学习指南/26_SFT与LoRA全流程/逐讲学习/02 按来源切分并理解拼接边界|上一讲]] · [[01_学习指南/26_SFT与LoRA全流程/逐讲学习/04 运行CPU和GPU训练并恢复状态|下一讲]]

## 本讲要解决的问题与前置

模型已经会一些基础任务，我们希望调整少量参数学习指定格式，而不是更新全部权重。本讲把LoRA写成一个小线性层，再接入Transformer。前置：上一讲的切分、[[01_学习指南/05_数学概率与优化/00 数学概率优化学习地图|矩阵乘法与梯度]]、[[01_学习指南/06_PyTorch训练闭环/00 PyTorch训练闭环学习地图|参数与优化器]]。矩阵形状不熟时先复习，不需要现在掌握低秩证明。

快速顺序：先看线性层 → 看A/B形状 → 运行初始化比较 → 查看冻结 → 修改rank。本讲读 `model.py` 的LoRALinear与add_lora。

## 概念与直觉：只学习一个受限制的增量

线性层可写作 `y = x Wᵀ`，这里PyTorch的权重W形状是 `[输出维度, 输入维度]`。LoRA把更新写成 `ΔW = (alpha / rank) B A`，A形状 `[rank, 输入维度]`，B形状 `[输出维度, rank]`。计算时先把x投影到rank维，再投影回输出维；原W冻结，只训练A和B。

rank是中间维度，限制增量矩阵最多有多少独立方向；它不是“模型等级”或准确率。alpha控制增量缩放。本例选择alpha等于rank，缩放恒为1，使rank2与rank8比较时不同时改变缩放。真实项目可分别调这两个参数，但需记录方案。

dropout是训练时随机把部分分支输入设为0、缩放保留值的正则化方法，用来降低对局部模式的依赖。本实验默认为0，恢复训练测试用0.2检查随机状态；它不保证消除过拟合。target modules表示注入适配器的层，本例选q_proj、v_proj、lm_head，分别影响注意力查询、值表示和最终词表分数。

“小补丁”类比帮助记住基础权重不动，但实际增量是矩阵乘积，训练仍需前向、反向和保存激活；不是修改几句提示词。[LoRA原论文](https://arxiv.org/abs/2106.09685)说明了这种低秩参数化方法。

## 最小示例：为什么初始输出完全相同

VS Code工程内新建 `lesson_03.py`：

```python
import torch
from torch import nn
from model import LoRALinear

torch.manual_seed(1)
base = nn.Linear(3, 2, bias=False)
adapted = LoRALinear(base, rank=1, alpha=1).eval()
inputs = torch.tensor([[1.0, 2.0, 3.0]])
print("A形状：", tuple(adapted.lora_a.shape))
print("B形状：", tuple(adapted.lora_b.shape))
with torch.no_grad():
    print("初始差值：", (base(inputs) - adapted(inputs)).abs().max().item())
print("Base可训练：", base.weight.requires_grad)
```

工程终端执行 `& ..\..\..\.venv\Scripts\python.exe lesson_03.py`。预期A为 `(1, 3)`，B为 `(2, 1)`，差值0.0，Base可训练False。

## 逐步讲解与接入顺序

`nn.Linear(3,2,bias=False)`输入3个数输出2个数，不使用额外偏置。A随机初始化，B全零，因此初始BA全零，输出等于Base。不能把A、B都设零：那会使两个因子的首步梯度都被另一因子的零阻断。

`eval()`关闭dropout训练行为；`no_grad()`只关闭这段比较的梯度记录，它们用途不同。`requires_grad=False`才明确冻结Base。执行 `add_lora` 时先冻结全模型，然后替换目标层，新的A/B默认可训练；优化器只接收这些可训练参数。

微型模型原始15008个参数。rank2新增508个，rank8新增2032个；总参数分别15516和17040。少量训练参数不代表Base不占内存，因为前向仍必须读取它。模型没有真实预训练语言知识，没有下载权重。

计算508的过程：两个32→32层各有 `2×(32+32)=128` 个增量参数，32→94词表头有 `2×(32+94)=252` 个；128+128+252=508。rank8按相同公式是2032。这里还没有优化器状态、梯度或激活内存。

## 动手：看到真正发生更新的参数

在工程README的CPU实验命令运行完后，读 `training.py`：优化器接收 `[parameter for parameter in model.parameters() if parameter.requires_grad]`。这个筛选逐个保留允许训练的参数，不为冻结权重维护AdamW状态。独立查看 `named_parameters()` 的名称与requires_grad：只有lora_a、lora_b应为True。

先不要为了“更多层更强”把embedding加入targets。本工程只支持已列出的三个线性层，错误名称会拒绝；真实模型的模块路径需要自己检查，不能套用另一个架构的名字。

## 常见错误与排查

- rank为0或超过层维度：检查正整数和最小输入输出维度，本例拒绝。
- 输出一开始就变了：检查B是否为零、dropout与模式、是否意外改了Base；同一输入在eval下比较。
- Base也更新：检查requires_grad及优化器参数列表，不能只相信文件名叫lora。
- 重复注入：不要在同一模型连续调用add_lora；从原始Base复制开始。
- CPU/GPU混用：模型和输入需放同一设备；适配器初始化继承Base设备和dtype。

## 练习与完成标准

### 跟做：计算参数数目

计算3→2层rank1新增多少参数。完成标准是区分原W与新增A/B。

> [!example]- 参考答案与解析
> 原W有2×3=6个；A有1×3=3个，B有2×1=2个，新增5个。若带偏置，Base偏置也保留，但本例不训练它。

### 独立：解释alpha=8、rank=2

写出增量缩放，并说明能否断言质量更高。

> [!example]- 参考答案与解析
> 缩放4。相同A/B时增量扩大4倍，但优化动态也改变，可能不稳定，不能从缩放直接推导质量。需同数据、固定评估协议比较。

### 迁移：只改lm_head会怎样

不用运行，先写假设、对照与判断指标。完成标准含“尚未测量”的标记。

> [!example]- 参考答案与解析
> 假设格式任务只改输出头已足够；与固定rank的q/v/head配置比较，保持训练数据、更新数和种子规则，记录验证质量、loss、参数量和耗时。结果未运行前不能写成有效结论。

## 继续学习

> [!next] 下一步
> [[01_学习指南/26_SFT与LoRA全流程/逐讲学习/04 运行CPU和GPU训练并恢复状态|下一讲：运行CPU和GPU训练并恢复状态]]

> [!info]- 练习与记录
> [[01_学习指南/26_SFT与LoRA全流程/示例工程/README#代码导航|查看源码]] · [[01_学习指南/26_SFT与LoRA全流程/示例工程/README#先运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 26：SFT与LoRA全流程|本单元完成清单]]
