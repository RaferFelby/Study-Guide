---
title: 第 3 讲：读懂特殊 token 与对话模板
tags:
  - chat-template
  - special-token
  - tool-calling
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 3 讲：读懂特殊 token 与对话模板

> [!nav] 页面导航
> [[01_学习指南/10_Tokenizer对话模板与训练样本/00 Tokenizer 对话模板与训练样本学习地图#学习顺序|单元 10：Tokenizer 对话模板与训练样本]] · [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/02 亲手训练字节BPE并编码新文本|上一讲]] · [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/04 给 assistant 目标构造 labels|下一讲]]


若已做 [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/02 亲手训练字节BPE并编码新文本|BPE 补充实验]]，从本讲起切回原 `tokenizer.py`。本页的特殊 token 编号不属于 BPE 实验的字节词表。

## 为什么聊天记录需要模板

如果把一段对话直接接成“你好今天天气如何晴”，模型看不出谁在说话，也看不出消息在哪里结束。chat template（对话模板）规定角色、消息边界、通道或工具路由怎样串成模型输入。模板最终也会变成 token ID 序列。

常见角色有 `system`（系统行为指令）、`user`（用户输入）、`assistant`（模型消息）和 `tool`（工具返回）。角色是消息数据字段；真实模型可能把它编码为专用 token，也可能编码成普通文本。拼写看起来特殊，不代表它必定是单个 token ID。

## 特殊 token 先分清职责

- **BOS（beginning of sequence）**：序列开头标记，有些模型使用，有些模板不加。
- **EOS（end of sequence）**：生成或训练目标中的序列终止标记。它与“某一条消息结束”可能不同。
- **PAD（padding）**：批次中用来补齐短序列长度的占位 token。它不是文本内容，也不应成为有效训练目标。
- **UNK（unknown）**：词表无法表示内容时的未知标记。有些 byte-fallback tokenizer 可以避免很多输入落到 UNK；具体取决于 tokenizer。
- **消息起止/分隔符**：本工程用 `<|im_start|>`、`<|im_sep|>` 和 `<|im_end|>` 教学。名字来自常见展示风格，不保证所有模型使用相同 ID 或相同结束语义。
- **工具路由**：常见做法是 assistant 消息包含收件人/工具名，之后出现工具回复，再由 assistant 总结。工具调用是一种结构化 assistant 动作，不能只看正文猜测。

## 最小模板示例

示例输入是：`user: 天气？`，然后 `assistant: 我来查询。`。本单元采用一个简化格式：

```text
<|bos|><|im_start|>user<|im_sep|>天气？<|im_end|>
<|im_start|>assistant<|im_sep|>我来查询。<|im_end|><|eos|>
```

逐段看：`BOS` 打开整条样本；`IM_START` 开始消息；角色文字说明说话方；`IM_SEP` 切开头部和正文；`IM_END` 结束一条消息；最后的 `EOS` 结束这条训练序列。具体模型可能用不同结构，也可能让一条 assistant turn 包含多条消息。

运行演示，在 `示例工程` 目录打开终端执行：

```powershell
..\..\..\.venv\Scripts\python.exe demo.py
```

程序显示 assistant 发起的 `to=weather` 路由头、tool 回复以及最终回答。角色/路由是序列结构的一部分；示例模板只是教学约定，不是任何具体模型的 chat template。

## 工具调用是一轮多消息交互

本工程工具样本按以下顺序排列：

1. user 提问；
2. assistant 写 `recipient=weather` 并输出调用内容；
3. `tool` 消息写工具返回结果；
4. assistant 根据工具结果回答用户。

工具调用常由 assistant 发出，因此“只监督 assistant 消息”会把调用内容纳入监督，而 tool 结果不自动纳入。不同微调目标可能会监督工具输出或通道头部；要以任务目标和框架规定为准。现实模板还可能包含 `tool_calls`、`name`、通道、JSON 参数等字段。本示例仅有 role/content/recipient，不处理任意复杂工具协议。

## 在真实模型里使用模板

Hugging Face Transformers 提供 `tokenizer.apply_chat_template(messages, ...)`，用 tokenizer 所带模板格式化消息。`add_generation_prompt=True` 通常在对话尾部追加 assistant 起始头，告诉模型接下来该生成 assistant 消息；用于训练时通常不加这个生成前缀。请查看 [官方 chat template 文档](https://huggingface.co/docs/transformers/main/en/chat_templating)。

若调用 `apply_chat_template(..., tokenize=False)` 得到字符串，再单独调用 tokenizer，通常要关闭后续的 `add_special_tokens`，否则模板已有的 BOS/EOS 等可能重复添加。优先按所用版本文档直接让模板 tokenizer 化，并用实际 token ID 检查边界。

## 练习

**跟做：** 打开 `demo.py`，将天气问题改为一个数学问题，保持 assistant、tool、assistant 三个后续步骤。预期仍有四条消息。

**独立：** 画出 `[BOS, user 消息, assistant 工具调用, tool 回复, assistant 回答, EOS]` 的顺序，并标出每个消息边界。

**迁移：** 在某模型模板里发现 `</s>` 出现在每条消息后，另一个模型只有 assistant 轮末尾出现 `eos_token`。写出你会查的配置和模板信息，不凭可见字符串直接替换。

> [!example]- 参考答案与解析
> 修改 demo 的 user `content`，比如“1+1 等于几？”，并把 recipient 改为 `calculator`，assistant 工具请求改为 `1+1`，tool 返回 `2`。样本依然是四个消息，证明结构不依赖天气文本。
>
> 画图时把消息头和正文区分开。工具调用是 assistant 消息，其后 tool 结果以 tool 角色返回；EOS 是整个样本终止标记。某些模型的消息结束 token 本身还区分普通结束、assistant turn 结束和交接给工具。
>
> 查 tokenizer 的 special token map、chat template、模型配置/文档和 Transformers 版本；在模型目标 checkpoint 上运行模板，再打印 token ID。EOS 与 message-end 语义不能只由字符串外观推断。

## 常见错误

- 将 `IM_END` 和 `EOS` 当成同一种边界：可能改变 turn 结束或继续生成行为。
- 把 role 名称当成固定 ID：模板可能将它编码成普通字节/子词，也可能使用专用 ID。
- 文本模板后又无条件添加 special tokens：可能产生重复起始或结束符。
- 以为所有模型都接受本工程的 `<|im_start|>`：ID 与语义必须来自模型自己的 tokenizer/template。

> [!nav] 路线续读
> 若本讲已到当前路线列出的范围末尾，返回原阶段继续下一项或检查产物；继续单元学习时沿下方“下一讲”。
>
> - [[00_学习路线/02 学习Agent与RAG应用#阶段 5：审计、安全与整合|学习Agent与RAG应用 · 阶段 5：审计、安全与整合]]

## 继续学习

> [!next] 下一步
> [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/04 给 assistant 目标构造 labels|下一讲：给 assistant 目标构造 labels]]

> [!info]- 练习与记录
> [[01_学习指南/10_Tokenizer对话模板与训练样本/示例工程/README#代码导航|查看源码]] · [[01_学习指南/10_Tokenizer对话模板与训练样本/示例工程/README#运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 10：Tokenizer、对话模板与训练样本|本单元完成清单]]
