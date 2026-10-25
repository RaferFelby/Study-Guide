---
title: 第 2 讲：计算回答概率并只统计completion
tags: [learning, dpo, preference]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 2 讲：计算回答概率并只统计completion

> [!nav] 页面导航
> [[01_学习指南/33_DPO与偏好优化/00 DPO与偏好优化学习地图#学习顺序|单元 33：DPO与偏好优化]] · [[01_学习指南/33_DPO与偏好优化/逐讲学习/01 构造同一问题的chosen与rejected偏好|上一讲]] · [[01_学习指南/33_DPO与偏好优化/逐讲学习/03 用冻结参考与beta读懂DPO损失|下一讲]]

## 本讲要解决的问题与前置

DPO需要比较两个回答的概率。概率怎样变成一个数？为什么问题和padding不能算进回答概率？前置 [[01_学习指南/05_数学概率与优化/00 数学概率优化学习地图|对数与概率]]、[[01_学习指南/06_PyTorch训练闭环/00 PyTorch训练闭环学习地图|张量形状]]、[[01_学习指南/26_SFT与LoRA全流程/逐讲学习/01 整理指令数据并只监督答案|回答掩码]]。

## completion、条件概率与对数

completion是prompt之后的完整回答。本例chosen三个token（ok、颜色、EOS），rejected五个token（多两个detail）。因果语言模型逐token预测：回答概率是每个回答token在问题与已知前缀下的条件概率乘积；取log后变为这些log概率相加。

例如三个token概率都0.5，序列概率0.125，log概率3×log(0.5)。log概率通常负数；-2比-4大，表示序列概率更高。log可以避免很多小数相乘下溢，不能把负号解释成负概率。

标准本例DPO用回答log概率的**和**，不默认按长度平均。平均是不同统计，不可随便替换目标；不同DPO变体也需明确，不把所有偏好损失称同一公式。

## 最小示例：均匀词表下只看长度

新建lesson_02.py：

```python
import torch
from data import TOKENS, batch_sequences, make_pairs
from objectives import sequence_logps

pair = make_pairs()[0]
inputs, labels = batch_sequences([pair["prompt"]] * 2,
                                 [pair["chosen"], pair["rejected"]])
logits = torch.zeros(*inputs.shape, len(TOKENS))
logps, counts = sequence_logps(logits, labels)
print("形状：", tuple(logits.shape), tuple(labels.shape))
print("回答token数：", counts.tolist())
print("log概率和：", logps.tolist())
print("每token平均：", (logps / counts).tolist())
```

运行 `& ..\..\..\.venv\Scripts\python.exe lesson_02.py`。预期logits形状(2,9,45)、labels(2,9)，回答计数[3,5]，log概率和约[-11.41999,-19.03331]，平均两项都约-3.80666。浮点末位允许变化。

## 逐步讲解形状与位移

B=2是两条序列，T=9是最长prompt4+回答5，V=45是词表。短序列后面补pad。logits[B,T,V]在每个位置给下一token的分数，不是已经归一化的概率。

batch_sequences把prompt和padding的labels设-100，回答含EOS保留真实ID。sequence_logps使用logits[:, :-1]预测labels[:, 1:]：输入位置t预测下一个位置t+1。第一回答位于索引4，应由最后prompt位置索引3预测；不位移就会让模型“看着答案预测自己”。

log_softmax先把分数转为log概率，gather按目标ID取每个位置的值；无监督位置临时用安全ID0索引，再乘mask消除其贡献。每行至少有一个有效回答，超词表标签和空监督拒绝。

短回答较高概率在此来自长度，不说明内容更正确。这也是为什么只看chosen_raw_logp_wins会误导：Base还不会问答也可能喜欢短序列。DPO还要减去reference相对倾向，第3讲解释。

## 动手与常见错误

打印labels，确认前四位-100、EOS仍计数、短回答padding不计。把无监督位置logits任意改大，log概率和应不变；回答预测位置改变会变。练习只改自己的脚本，不改公共词表。

sum换mean并非小格式调整，会改变长短回答的目标。PAD和EOS用途不同：PAD只是补批次形状，EOS是结束，应纳入回答概率。标签屏蔽不等于把prompt从输入删除。

## 练习与答案

### 跟做：解释3与5

完成标准是指出含EOS、不含prompt/pad，并说明-11比-19表示更高序列概率。

> [!example]- 参考答案与解析
> 两回答3/5个token，均匀词表每token概率1/45，和为3或5倍log(1/45)。差异是长度造成，不是事实裁判。

### 独立：不位移会怎样

提示：看第一回答token已有输入。完成标准是说明预测目标错位和答案泄漏。

> [!example]- 参考答案与解析
> 同一位置输入已经有目标token，模型可能学复制自身而非下一token。正确为prompt末位预测首回答，回答末前位预测EOS。

### 迁移：真实Tokenizer

列出概率比较前的对齐条件。完成标准是同prompt、同模型词表/模板、completion边界、EOS/pad及截断规则。

> [!example]- 参考答案与解析
> 两侧用一致聊天模板和Tokenizer，核对回答边界与因果位移，不重复特殊token，不截掉一侧而保留另一侧。本固定词表ID不能给外部模型。

## 继续学习

> [!next] 下一步
> [[01_学习指南/33_DPO与偏好优化/逐讲学习/03 用冻结参考与beta读懂DPO损失|下一讲：用冻结参考与beta读懂DPO损失]]

> [!info]- 练习与记录
> [[01_学习指南/33_DPO与偏好优化/示例工程/README#代码导航|查看源码]] · [[01_学习指南/33_DPO与偏好优化/示例工程/README#先运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 33：DPO与偏好优化|本单元完成清单]]
