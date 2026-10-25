---
title: 单元 10：Tokenizer 对话模板与训练样本
tags: [learning, unit-map]
updated: 2026-10-26
cssclasses: ["guide-page", "guide-map"]
---

# 单元 10：Tokenizer 对话模板与训练样本

> [!nav] 页面导航
> [[01_学习指南/00 学习目录#二、数学、数据与模型基础|返回主题目录]] · [[00_学习路线/00 选择你的学习方向|选择学习方向]]
>
> 本页：[[#前置与完成标准|前置]] · [[#学习顺序|课表]] · [[#完成后继续|完成后]]

## 今天先做什么

> [!start] 从第 1 讲的最小例子开始
> 把文本整理成正确的训练样本。打开 [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/01 把文本编码成 token ID|第 1 讲：把文本编码成 token ID]]，先完成其中第一个最小例子，再用自己的话解释结果。

## 前置与完成标准

- 需要知道列表按顺序保存多个值、函数返回值如何接收，以及 Python 的 `for` 和 `if`。忘了列表与循环时，先回看 [[01_学习指南/01_Python工程化/逐讲学习/01 运行Python并统计工单|单元 01 第 1 讲]]。
- 需要认识序列长度、batch（一次并行处理的样本组）与张量形状；相关内容见 [[01_学习指南/06_PyTorch训练闭环/逐讲学习/01 Tensor设备与广播|单元 06 第 1 讲]]。
- 因果语言模型逐位置预测下一个 token，见 [[01_学习指南/08_Transformer从零实现/逐讲学习/06 对齐自回归目标与交叉熵|单元 08 第 6 讲]]。本单元会重新用最小序列推导对齐方式，不要求先背公式。

**本单元完成标准：** 解释词表、模板、labels 与掩码，并拒绝一条错误样本。

## 学习顺序

本单元共 7 讲。课表表示单元内阅读顺序，按所选方向需要学习。

| 顺序 | 本讲任务 |
|---|---|
| 01 | [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/01 把文本编码成 token ID\|把文本编码成 token ID]] |
| 02 | [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/02 亲手训练字节BPE并编码新文本\|亲手训练字节BPE并编码新文本]] |
| 03 | [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/03 读懂特殊 token 与对话模板\|读懂特殊 token 与对话模板]] |
| 04 | [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/04 给 assistant 目标构造 labels\|给 assistant 目标构造 labels]] |
| 05 | [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/05 用两种 mask 组成批次\|用两种 mask 组成批次]] |
| 06 | [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/06 检查工具轮次与模板边界\|检查工具轮次与模板边界]] |
| 07 | [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/07 完成训练样本验收\|完成训练样本验收]] |

## 运行配套工程

1. 用 VS Code 打开本页同级的 `示例工程` 文件夹。
2. 在该目录的 PowerShell 终端运行演示：

   ```powershell
   ..\..\..\.venv\Scripts\python.exe demo.py
   ```

   这条命令调用仓库根目录的共享 Python 环境运行 `demo.py`，不下载模型，也不需要 GPU。
3. 运行测试：

   ```powershell
   ..\..\..\.venv\Scripts\python.exe -m pytest -q
   ```

   `-m pytest` 让当前解释器启动 pytest，`-q` 减少逐项输出。预期所有测试通过；具体数量以工程中的测试文件为准。
4. 打开 [tokenizer.py](./示例工程/tokenizer.py) 与 [chat_data.py](./示例工程/chat_data.py)，跟着第 1 至第 6 讲逐段阅读。

## 重要限制

模板主工程是用于讲解的 UTF-8 字节回退：每字节一个 ID，能完整还原文本，但 token 数会偏多；该主工程不是 BPE/Unigram 实现；第 2 讲另有小规模字节 BPE 算法，尚无 Unigram 实现，也不是可喂给模型的生产 tokenizer。SentencePiece 支持 BPE 和 Unigram，并提供 byte fallback 选项；真实模型的词表、特殊 ID 与模板要从对应 checkpoint 读取，不能仅凭 token 的可见拼写猜测。可查 [SentencePiece 官方说明](https://github.com/google/sentencepiece/blob/master/doc/options.md) 与 [符号说明](https://github.com/google/sentencepiece/blob/master/doc/special_symbols.md)。

Hugging Face 文档建议直接使用模型 tokenizer 的 `apply_chat_template`，以确保模板与该模型匹配；若模板输出字符串后再分词，要避免重复添加 special tokens。训练时是否监督 assistant 的头部、工具调用和 tool 回复属于数据目标选择，要在此处明确并测试，不存在适用于所有模型的同一模板。参考 [Transformers chat template 文档](https://huggingface.co/docs/transformers/main/en/chat_templating) 与[入门说明](https://huggingface.co/docs/transformers/main/en/chat_template_basics)。

## 相关课程

上一单元：[[01_学习指南/09_主流大模型架构与参数估算/00 主流大模型架构与参数估算学习地图|单元 09：主流大模型架构与参数估算]]。相关后续：[[01_学习指南/11_LLM_API与Prompt/00 LLM API 与 Prompt 学习地图|LLM API、Prompt 与结构化输出]]。

## 工程与记录

> [!info]- 源码、运行说明与作者记录
> - [[01_学习指南/10_Tokenizer对话模板与训练样本/示例工程/README|在 VS Code 打开源码与运行说明]]
> - [[90_参考与维护/单元验证/10 Tokenizer对话模板与训练样本验证记录|按需查作者验证与限制]]
> - [[90_参考与维护/课程覆盖/09 Tokenizer、对话模板与训练样本（P0）|按需核对知识与验收映射]]

## 完成后继续

> [!next] 回到当前方向
> 回到你正在学习的方向，核对本阶段剩余任务；下列方向任选当前这一条。
>
> - [[00_学习路线/02 学习Agent与RAG应用#阶段 5：审计、安全与整合|只补文本编码与模板后：返回 Agent 阶段 5]]
> - [[00_学习路线/02 学习Agent与RAG应用#阶段 6：按项目需要扩展|为推理策略补完整样本基础后：返回 Agent 阶段 6]]
> - [[00_学习路线/03 学习模型训练与大模型算法#阶段 2：理解模型与样本|学习模型训练与大模型算法 · 阶段 2]]
> - [[00_学习路线/05 学习推理系统与GPU工程#完整单元与工程扩展|为 GPU 完整实验学完本单元后：返回阶段 2 的完整单元与工程扩展]]

> [!info]- 记录本次学习
> [[02_学习记录/01 全课程完成清单#单元 10：Tokenizer、对话模板与训练样本|本单元完成清单]] · [[02_学习记录/00 我的学习记录#下次从哪里继续|写下次继续的位置]]
