---
title: 第 4 讲：给 assistant 目标构造 labels
tags:
  - labels
  - causal-lm
  - loss-mask
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 4 讲：给 assistant 目标构造 labels

> [!nav] 页面导航
> [[01_学习指南/10_Tokenizer对话模板与训练样本/00 Tokenizer 对话模板与训练样本学习地图#学习顺序|单元 10：Tokenizer 对话模板与训练样本]] · [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/03 读懂特殊 token 与对话模板|上一讲]] · [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/05 用两种 mask 组成批次|下一讲]]

## 训练要让模型学什么

因果语言模型（causal language model）在每个位置读取当前位置之前和当前的上下文，预测下一个 token。labels（标签）是每个预测位置的正确答案 token ID。对话微调通常不希望模型从 user 提问、system 指令和 tool 原始输出中学习“以 assistant 身份复述它们”，因此会把某些 label 标记为忽略。

`-100` 是 PyTorch `CrossEntropyLoss` 常用的忽略标签值：这类目标不贡献 loss（损失值）与对应的梯度。该值不是词表 token ID，不能放进 `input_ids` 给 embedding 查表。参考 [PyTorch CrossEntropyLoss 文档](https://docs.pytorch.org/docs/stable/generated/torch.nn.CrossEntropyLoss.html)。

## 最小 next-token 对齐

假设实际输入 token 序列是：

```text
位置：       0     1   2   3
input_ids： BOS   A   B   EOS
```

位置 0 的 logits（模型为下一个 token 给出的未归一化分数）要预测位置 1 的 `A`；位置 1 预测 `B`；位置 2 预测 `EOS`。最后位置没有序列内的下一个目标。因此对自定义 loss，常写成：

```python
shifted_logits = logits[:, :-1, :]
shifted_labels = labels[:, 1:]
```

这两片分别删掉最后一行预测和第一个无法由序列内上下文预测的 label，时间位置因此对齐。若用封装的因果模型并把 `labels` 传进模型，先看所用模型 API：许多模型会在内部移位，因此应该给完整的、尚未手动 shift 的 labels。Hugging Face GPT-J 文档明确说明其 labels 在模型内部移位；其他类和版本仍需检查对应实现/文档。[GPT-J 官方源码说明](https://github.com/huggingface/transformers/blob/main/src/transformers/models/gptj/modeling_gptj.py)。

> [!warning] 不要移位两次
> 若模型内部已 shift，再传入手动 shift 后的 labels，会让目标再错开一位。必须先确认 loss 由谁计算，再决定是否自己 shift。

## assistant-only 标签如何构造

配套 `chat_data.py` 保留完整 `input_ids`，创建同长 `labels`：

- BOS、消息开始标记、角色头、用户正文、tool 正文都用 `-100`；
- assistant 正文的 token ID 保留为标签；
- assistant 的 `IM_END` 以及最终 `EOS` 也保留，让模型学习怎样结束回答/样本。

每个 input 位置仍然存在，即使该位置 label 是 `-100`。这样模型还能把此前 user/system/tool 内容作为上下文，只是那些位置不作为目标。这是“读入上下文”和“对该位置的下一个 token 计算监督”两个不同问题。

在 VS Code 打开 `示例工程/chat_data.py`，找到 `encode_messages`。它对每条消息按顺序执行：验证 role/content；编码头部；为头部追加忽略标签；编码正文；仅当角色为 assistant 时复制正文 ID 到 labels；追加消息结束 token；若最后一条是 assistant，再追加 EOS。

运行测试并观察监督数：

```powershell
..\..\..\.venv\Scripts\python.exe -m pytest -q
```

`count_supervised_tokens` 统计 labels 中不等于 `-100` 的数量。一个 assistant 回答若内容为空，仍可能只监督结束标记；真实数据应检查有效监督 token 数而不是只看消息条数。

## 练习

**跟做：** 为 user `hi`、assistant `ok` 列出 `input_ids` 与 labels 的相同位置关系；指出 `hi` 为什么仍在 input 中。

**独立：** 对 `[BOS,A,B,EOS]`，填写 logits 位置 0、1、2 分别预测哪个 token，并说明位置 3 是否有序列内目标。

**迁移：** 某自定义训练循环先执行 `logits[:, :-1]` 和 `labels[:, 1:]`，又把它们传给会在内部 shift labels 的模型。判断风险并写出检查步骤。

> [!example]- 参考答案与解析
> labels 与 input 长度相等，但 `BOS`、user 的结构和正文位置写 `-100`；assistant 的正文 `o`,`k` ID、`IM_END` 与 `EOS` 保留。`hi` 要留在 input，让模型读到提问；屏蔽 label 并不等于删掉上下文。
>
> logit 0 预测 A，logit 1 预测 B，logit 2 预测 EOS。位置 3 没有后续 token，因此该位置不参与这段序列的 next-token loss。
>
> 双重 shift 会错位。查模型对应版本 forward 文档/源码，检查 labels 接口是否内部右移/左移；选一种做法：传未移位 labels 给内部处理的模型，或自己移位后调用不再移位的自定义 loss，并用 `[BOS,A,B,EOS]` 小例子断言对齐。

## 常见错误

- labels 长度与 input_ids 不一致：先逐样本断言长度相同。
- 把 `-100` 放进 input_ids：它不是词表 ID，会导致 embedding 越界。
- 把 user content 改成 PAD：会删掉模型需要阅读的上下文。
- 所有样本都被 mask：loss 没有有效 token，应检查 assistant 消息、模板角色和监督策略。

## 继续学习

> [!next] 下一步
> [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/05 用两种 mask 组成批次|下一讲：用两种 mask 组成批次]]

> [!info]- 练习与记录
> [[01_学习指南/10_Tokenizer对话模板与训练样本/示例工程/README#代码导航|查看源码]] · [[01_学习指南/10_Tokenizer对话模板与训练样本/示例工程/README#运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 10：Tokenizer、对话模板与训练样本|本单元完成清单]]
