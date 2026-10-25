---
title: 第 5 讲：用两种 mask 组成批次
tags:
  - padding
  - attention-mask
  - batching
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 5 讲：用两种 mask 组成批次

> [!nav] 页面导航
> [[01_学习指南/10_Tokenizer对话模板与训练样本/00 Tokenizer 对话模板与训练样本学习地图#学习顺序|单元 10：Tokenizer 对话模板与训练样本]] · [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/04 给 assistant 目标构造 labels|上一讲]] · [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/06 检查工具轮次与模板边界|下一讲]]

## 为什么需要 padding

神经网络一次计算一批（batch）样本时，通常需要同一批序列长度相同。较短样本需要补到最长长度，这叫 padding（填充）。比如长度 3 和 5 的两条样本要组成矩形：短样本多出两个 PAD 位置。

每个 PAD 既不是真实上下文，也不应参与监督。为此需要两种不同职责的标记：`attention_mask` 说明哪些输入位置有效，`labels=-100` 说明哪些预测目标不进入 loss。注意力 mask 本身不会自动替代监督标签 mask。

## 一个小批次

假设两条输入分别是 `[BOS,A,EOS]` 和 `[BOS,A,B,C,EOS]`。右 padding 后：

```text
input_ids:      [BOS,A,EOS,PAD,PAD]
attention_mask: [ 1, 1,  1,  0,  0]
labels:         [-100, A, EOS, -100, -100]  # 仅为说明的简化目标
```

attention mask 中 1 表示真实输入，0 表示填充；labels 中 `-100` 表示忽略监督。真实标签还要依照上一讲的 causal shift 规则对齐。工程 `pad_batch` 会把 labels 的 padding 部分设为 `-100`，并与 input 同侧补齐。

## 训练和生成的左右选择

- **右 padding：**真实 token 都从左边开始，尾部补 PAD。常用于训练批次，且与常见训练序列布局直观一致。模型具体支持方式仍要查接口。
- **左 padding：**开头补 PAD，让批次中每条有效序列的末尾都落在相同列。常见批量生成 API 使用左 padding，因为生成通常从每条输入最后一个有效位置继续；Hugging Face 的 LLM 教程也建议生成输入使用 `padding_side="left"`。[官方生成教程](https://huggingface.co/docs/transformers/main/llm_tutorial)

左右 padding 的选择不能只改 token 列表：`input_ids`、attention mask、labels 要一起平移，位置编码/position IDs 也要由模型 API 正确处理。若手写生成循环，还要确认从哪个位置读取 logits。

## 动手运行

在示例工程目录运行：

```powershell
..\..\..\.venv\Scripts\python.exe -c "from chat_data import encode_messages, pad_batch; a=encode_messages([{'role':'user','content':'q'},{'role':'assistant','content':'a'}]); b=encode_messages([{'role':'user','content':'long'},{'role':'assistant','content':'answer'}]); print(pad_batch([a,b], padding_side='right')); print(pad_batch([a,b], padding_side='left'))"
```

这条命令构造短、长两个样本，并分别打印左右填充批次。预期两次的矩阵宽度相同；右 padding 的短样本以 PAD/0/-100 结尾，左 padding 的短样本以 PAD/0/-100 开头。PAD 是 ID 0 的本工程约定，真实 tokenizer 的 PAD ID 可以不同。

## 常见错误排查

1. 如果三组矩阵长度不同，检查是不是只给 `input_ids` padding 而没 padding labels 或 mask。
2. 如果 padding 位置 `attention_mask=1`，模型仍会把填充当作有效上下文。
3. 如果有效 input token 的 `attention_mask=0`，上下文会被忽略。
4. 如果 PAD 标签不是 `-100`，训练可能在学习输出填充符。
5. 左 padding 生成结果异常时，检查模型位置 ID 与读取最后有效位置的逻辑；不能只以本工程列表测试代替真实模型验证。

## 练习

**跟做：** 用 `pad_batch` 对一个 2-token 和一个 4-token 的虚构样本分别做左右 padding，数出每行 1 与 0 的个数。

**独立：** 解释为什么 `attention_mask` 与 `labels` 两者都需要。

**迁移：** 设计训练 batch 和 batched generation 的 padding 选择，并列出真实模型上要验证的两件事。

> [!example]- 参考答案与解析
> batch 长度补到 4 后，左或右各有两个有效位置、两处 padding；具体 0 的位置随 padding_side 变化。完成标准是有效输入数仍为 2，新增位置均 mask 为 0。
>
> attention mask 控制输入侧有效位置；labels 的 `-100` 控制 loss 侧目标是否参与。assistant-only 训练中许多有效上下文位置（system/user）attention=1，但 labels=-100，二者不能合并。
>
> 训练一般先测试右 padding；批量生成常测试左 padding。真实验证需确认模型接受所选 padding/position IDs，以及 generation 从末尾有效 token 继续并且结果与逐条生成大致一致。

## 完成检查

- [ ] 能把 attention mask 与 label/loss mask 分别说清楚。
- [ ] 能画出左右 padding 后有效 token 的位置。
- [ ] 能说明为什么训练和 batched generation 可采用不同 padding 侧。

## 继续学习

> [!next] 下一步
> [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/06 检查工具轮次与模板边界|下一讲：检查工具轮次与模板边界]]

> [!info]- 练习与记录
> [[01_学习指南/10_Tokenizer对话模板与训练样本/示例工程/README#代码导航|查看源码]] · [[01_学习指南/10_Tokenizer对话模板与训练样本/示例工程/README#运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 10：Tokenizer、对话模板与训练样本|本单元完成清单]]
