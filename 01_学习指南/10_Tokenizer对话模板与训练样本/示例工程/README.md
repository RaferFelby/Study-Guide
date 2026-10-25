---
title: 单元 10 示例工程导航
tags:
  - code
  - tokenizer
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# 单元 10 示例工程

> [!nav] 页面导航
> [[01_学习指南/10_Tokenizer对话模板与训练样本/00 Tokenizer 对话模板与训练样本学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/01 把文本编码成 token ID|从第一讲开始：把文本编码成 token ID]]

此工程演示 UTF-8 字节回退、对话模板、assistant 监督标签和左右 padding。模板主工程不实现 BPE/Unigram；独立补充脚本提供小规模字节 BPE，不加载真实模型；代码只用 Python 标准库，测试用工作区共享环境中的 `pytest`。

## 运行

在 VS Code 打开本目录，并在该目录的 PowerShell 终端执行：

```powershell
..\..\..\.venv\Scripts\python.exe demo.py
..\..\..\.venv\Scripts\python.exe -m pytest -q
```

第一条运行演示；第二条用 pytest 发现并执行 `tests/test_*.py`。完整输出会因示例文本而不同，但应能看到 4 条消息、若干有效监督 token，测试全部通过。

## 代码导航

- [tokenizer.py](./tokenizer.py)：UTF-8 字节与教学用特殊 token 的双向转换。
- [chat_data.py](./chat_data.py)：消息模板、assistant labels、批次 attention mask 和 label padding。
- [demo.py](./demo.py)：端到端演示入口。
- [test_tokenizer.py](./tests/test_tokenizer.py)：编码往返、非法 ID 与 UTF-8 边界测试。
- [test_chat_data.py](./tests/test_chat_data.py)：标签屏蔽、工具轮次、模板标记与左右 padding 测试。
- [requirements.txt](./requirements.txt)：本工程最小依赖说明。

- [bpe_demo.py](./bpe_demo.py)：独立字节 BPE 训练、规则排序、编码与整体 UTF-8 解码；未接入 chat_data.py。
- [test_bpe_demo.py](./tests/test_bpe_demo.py)：频次、并列、重叠、样本边界、中文／空白往返、非法规则与截断字节。

按 [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/02 亲手训练字节BPE并编码新文本|BPE 详细课]]在本目录运行 `..\..\..\.venv\Scripts\python.exe bpe_demo.py`。新增 ID 从 256 开始，没有模板特殊 token；不要与 tokenizer.py 的偏移 6 混用。

## 教学边界

此 tokenizer 把一个 UTF-8 字节映射到一个 ID，可保证文本往返，但对中文会产生较长序列。真实模型使用自身训练得到的 BPE、Unigram 或其他 tokenizer，以及 checkpoint 专属的 special-token ID 和 chat template。不要把本示例的 ID 喂给真实模型。
