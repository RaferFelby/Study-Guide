---
title: 单元 10 参考工程验证记录
tags:
  - verification
  - tokenizer
updated: 2026-10-23
status: verified
cssclasses: ["guide-page", "guide-reference"]
---

# 单元 10 参考工程验证记录

> [[01_学习指南/10_Tokenizer对话模板与训练样本/00 Tokenizer 对话模板与训练样本学习地图|单元 10：Tokenizer 对话模板与训练样本]] · [[01_学习指南/10_Tokenizer对话模板与训练样本/示例工程/README|源码导航]]


## 字节 BPE 的训练与编码（2026-10-23，本轮）

本轮更新 [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/02 亲手训练字节BPE并编码新文本|BPE 详细课]]。新增独立 bpe_demo.py 和 30 项参数化检查，含重复语料计数、并列次序、非重叠替换、样本边界、规则验证、未见文本、中文／空白往返及截断 UTF-8。原 16 项模板与 tokenizer 测试一并通过。

- 在根共享 Python 3.13.12 下运行，本单元全部 **46 项测试通过**。新增源码／测试通过 Ruff 静态与格式检查。
- 本轮六单元合计 232 项测试；教材验证脚本最终完成 45 次独立进程调用，其中两次是预期的拒绝覆盖／回填失败，其余正常完成。本文只引用本单元对应记录，不把其他单元结果算成本单元测试。
- 共 29 段本轮教材 Python 片段经过 Ruff 格式整理，27 段完整脚本或定义片段通过静态检查与独立执行；2 段明确标注为函数内部的核心片段未作为独立脚本运行，行为由完整示例及测试检查。

检查证据：`.author-tools/hour-check-bpe-6355fa870fa742c0b5ea92df4ff8ed55.json`；教材独立调用、实际输出与数据库摘要保存在 `.author-tools/hour-20261023-0fb9922b9fbc486db7a13e97c7d69269/commands.json` 和 `summary.json`。作者工具的首次抽取把窗口内部片段当独立脚本导致 NameError，调整抽取范围后重跑；不是把该次失败记为成功。诊断工具首次处理超时输出时误判 str／bytes，修正后才取得堆栈证据。

范围限制：原模板 tokenizer 与 BPE 使用不同 ID 空间，未互换或改写 chat_data.py。没有真实模型、生产预分词、官方词表兼容或 Unigram 训练。 无依赖安装／升级，没有调用真实模型，也未完成 Obsidian 阅读视图的视觉验收。学习者完成标记没有自动勾选。以下保留原有历史记录。

## 验证范围

工程使用 Python 标准库实现一个 UTF-8 byte-fallback 教学 tokenizer、简化对话模板、assistant-only label、左右 padding 和 mask。测试只验证这些 Python 数据变换，不训练或下载语言模型。

## 环境和结果

- Python：3.13.12；pytest：8.4.2，来自工作区共享 `.venv`。
- 依赖：源码只用 Python 标准库；本次未安装或升级包。环境已有 PyTorch，但没有 Transformers、tokenizers 或 SentencePiece；本工程没有导入 PyTorch。
- 设备：本次是纯 CPU 数据处理，无 GPU 计算。
- `python -m pip check`：通过，未发现声明依赖冲突。
- `python -m ruff format .`：完成；`python -m ruff check .`：通过。
- `python -m pytest -q`：17 passed。
- `python demo.py`：退出码 0；样本报告 131 个输入 token、48 个有效监督 token，attention mask 长度为 131。当前工具捕获终端的中文显示乱码，因此输出中的文本可读性未在此终端验证；UTF-8 往返由单元测试覆盖。
- 限制：字节 ID、特殊 token 与模板仅为教学定义，不能直接用于真实 checkpoint。没有完成真实模型 tokenizer/template 集成验证或模型训练。

## 主要不变量

- 所有输入 ID 都在已知 special ID 或 256 个 byte ID 的范围内；文本 UTF-8 编码/解码应往返一致。
- labels 与 input_ids 等长；非 assistant 消息不参与本工程设定的监督。
- 对 assistant 内容、IM_END 和最终 EOS 保留监督；padding 标签为 -100。
- attention mask 只表达输入侧的有效位置；不能代替 labels 的监督屏蔽。
- 左右 padding 后各字段长度、token 相对顺序和对应 mask/label 位置一致。

## 可复核命令

从本目录进入 `示例工程`，运行 README 中的 demo 与 pytest 命令。以上命令和结果记录的是作者侧验证，不代表学习者已完成练习或 C09 验收。
