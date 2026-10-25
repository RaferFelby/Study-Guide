---
title: 模块 09 覆盖与验收
tags: [reference, coverage]
updated: 2026-10-24
cssclasses: ["guide-page", "guide-reference"]
---

# 模块 09 覆盖与验收

> [!nav] 页面导航
> [[90_参考与维护/01 课程覆盖索引|覆盖索引]]

## 模块 09：Tokenizer、对话模板与训练样本（P0）

教材状态：已编写；六讲教材与标准库示例见 [[01_学习指南/10_Tokenizer对话模板与训练样本/00 Tokenizer 对话模板与训练样本学习地图|单元 10 学习地图]]。

**学习内容**

- **K09-01** BPE、Unigram、SentencePiece 与字节回退；见 [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/01 把文本编码成 token ID|第 1 讲：把文本编码成 token ID]]；[[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/02 亲手训练字节BPE并编码新文本|BPE 详细课]]提供独立字节算法、手算、运行与答案，Unigram 仍为概念介绍，未运行生产 tokenizer 训练。
- **K09-02** BOS/EOS/PAD/UNK、角色和工具调用 token；见 [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/03 读懂特殊 token 与对话模板|第 3 讲：读懂特殊 token 与对话模板]]。
- **K09-03** padding、truncation、attention mask、chat template；见 [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/03 读懂特殊 token 与对话模板|第 3 讲：读懂特殊 token 与对话模板]]、[[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/05 用两种 mask 组成批次|第 5 讲：用两种 mask 组成批次]]、[[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/06 检查工具轮次与模板边界|第 6 讲：检查工具轮次与模板边界]]。
- **K09-04** input_ids、attention_mask、labels 与 loss mask；见 [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/04 给 assistant 目标构造 labels|第 4 讲：给 assistant 目标构造 labels]]、[[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/05 用两种 mask 组成批次|第 5 讲：用两种 mask 组成批次]]。
- **K09-05** causal LM 的标签移位：区分模型内部 shift 和自定义 loss 手动 shift，避免两次移位；padding mask 与监督 mask 作用不同；见 [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/04 给 assistant 目标构造 labels|第 4 讲：给 assistant 目标构造 labels]] 与 [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/07 完成训练样本验收|第 7 讲：完成训练样本验收]]。

**验收标准**

- [ ] **C09-01** 编码单轮、多轮和工具调用对话并逐段解释 token；操作见 [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/03 读懂特殊 token 与对话模板|第 3 讲：读懂特殊 token 与对话模板]]，综合验收见 [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/07 完成训练样本验收|第 7 讲：完成训练样本验收]]。
- [ ] **C09-02** 正确屏蔽不参与监督的 label；见 [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/04 给 assistant 目标构造 labels|第 4 讲：给 assistant 目标构造 labels]]。
- [ ] **C09-03** 分别验证训练和批量生成场景中的左右 padding，说明选择依据；见 [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/05 用两种 mask 组成批次|第 5 讲：用两种 mask 组成批次]]。
- [ ] **C09-04** 编写测试防止模板升级后出现重复特殊 token 或标签错位；见 [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/06 检查工具轮次与模板边界|第 6 讲：检查工具轮次与模板边界]] 和源码测试。
- [ ] **C09-05** 对 token `[BOS, A, B, EOS]`，解释 logits 的前三个位置分别监督 `A、B、EOS`；自定义 loss 时对齐 `logits[:, :-1]` 与 `labels[:, 1:]`，使用封装模型时先确认它是否内部移位；见 [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/04 给 assistant 目标构造 labels|第 4 讲：给 assistant 目标构造 labels]]。
- [ ] **C09-06** 检查至少三个样本的有效监督 token 数大于 0，并确认 user/system 的监督屏蔽与 padding 屏蔽符合训练目标；见 [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/07 完成训练样本验收|第 7 讲：完成训练样本验收]]。

参照 [Hugging Face 因果语言建模教程](https://huggingface.co/docs/transformers/tasks/language_modeling)，但不能将教程的数据处理配置未经检查直接套用到所有对话模型。


## 单元 10 原地图对照：原始模块映射

教材单元 10 对应原模块 09。知识条目和 C09-01 至 C09-06 验收映射见 [[90_参考与维护/课程覆盖/09 Tokenizer、对话模板与训练样本（P0）#模块 09：Tokenizer、对话模板与训练样本（P0）|课程覆盖台账]]；作者实际验证环境与结果见 [[90_参考与维护/单元验证/10 Tokenizer对话模板与训练样本验证记录|验证记录]]。
