---
title: 第 1 讲：把文本编码成 token ID
tags:
  - tokenizer
  - bpe
  - unigram
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 1 讲：把文本编码成 token ID

> [!nav] 页面导航
> [[01_学习指南/10_Tokenizer对话模板与训练样本/00 Tokenizer 对话模板与训练样本学习地图#学习顺序|单元 10：Tokenizer 对话模板与训练样本]] · [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/02 亲手训练字节BPE并编码新文本|下一讲]]

## 这讲要解决什么

模型不能直接查词典理解“你好”。它先把文本切成 token（供模型处理的文本片段），再把每片段映射为整数 token ID。你要弄清：为什么需要这个映射，tokenizer（分词器）如何切分文本，以及切分结果为什么不能随便换。

## 先认识字节与 token ID

字节是计算机存储文本时使用的基本数据单位之一。UTF-8 是常用的 Unicode 文本编码规则；一个中文字符通常占多个字节。教学工程把每个 UTF-8 字节加上固定偏移量 6 作为 ID：字节值 0 映射到 ID 6，字节值 255 映射到 ID 261。

在 VS Code 中打开 `示例工程/tokenizer.py`。最小操作如下：

```python
from tokenizer import decode_ids, encode_text

token_ids = encode_text("猫")
print(token_ids)
print(decode_ids(token_ids))
```

在工程目录终端运行：

```powershell
..\..\..\.venv\Scripts\python.exe -c "from tokenizer import encode_text, decode_ids; ids = encode_text('猫'); print(ids); print(decode_ids(ids))"
```

`-c` 让 Python 直接执行引号中的短语句，适合一次性观察结果。会看到 3 个字节 ID，第二行恢复为“猫”。UTF-8 的字节值可能因字符不同而变化，但解码后必须完全相同。原因是这个例子是一字节对应一个 token，并不是常见模型的子词切分。

`encode_text` 先用 `text.encode("utf-8")` 取得字节，再给每个字节加偏移；`decode_ids` 做相反操作，将连续字节收集起来再按 UTF-8 解码。遇到特殊 ID 时先解码前面的字节，再打印 special-token 拼写。无效 ID 会报错，不会悄悄编造文本。

## 为什么真实 tokenizer 会切得更聪明

若每个字节都单独占一个 token，文本序列会变长，模型每次注意力计算要处理更多位置。子词 tokenizer（subword tokenizer）会把常见字符片段合并成词表条目，以便在词表大小、序列长度和未见字符串处理能力之间折中。

- **BPE（Byte Pair Encoding，字节对编码）直觉：** 从较小单位开始，反复合并训练语料里常一起出现的相邻片段。常见词片段可能变成一个 token，罕见拼写仍能拆成更小部分。它的真实训练包含词频与合并顺序，不能只靠一句“合并常见字”复现完整 tokenizer。
- **Unigram（单元语法模型）直觉：** 从候选子词词表出发，为片段建立概率模型，再逐步删去不合适的候选，使整体文本能以较好的概率切分。它与 BPE 的“反复合并”训练机制不同。
- **SentencePiece：** 一套 tokenizer 工具和模型格式，可使用 BPE 或 Unigram 等算法；它把原始文本（含空格）作为输入处理，避免必须先依赖语言专用预分词器。它不是 BPE 的别名。
- **Byte fallback（字节回退）：** 遇到词表无法直接表示的字符时，退回其 UTF-8 字节表示。这样能降低未知字符彻底丢失的风险，但可能让该字符变成多个 token。

SentencePiece 官方参数说明列出 BPE、Unigram 和 byte fallback 选项：[SentencePiece options](https://github.com/google/sentencepiece/blob/master/doc/options.md)。不同模型的词表和预处理方式仍会不同，切分不是跨模型通用的。

## 动手操作与预期结果

1. 将命令中的“猫”换成 `你好，agent 🙂`，观察 ID 数量与字符数是否相等。预期不相等，因为中文、标点和 emoji 的 UTF-8 字节数不同。
2. 把 `decode_ids(token_ids)` 中的 IDs 改成 `[999]`。预期 `ValueError: 未知 token ID`，表示代码明确拒绝范围外 ID。
3. 把 `encode_text("猫")` 改成 `encode_text(3)`。预期 `TypeError`，因为文本编码函数只接收字符串。

若输出乱码或 UTF-8 解码报错，检查是否把一个字符的字节截断，或在列表里改坏 ID。不要对任意 byte ID 逐个独立调用 UTF-8 解码；一个中文字符需要若干字节合起来才完整。

## 练习

**跟做：** 用代码验证“中文猫🙂”经 `encode_text` 和 `decode_ids` 后相同。完成标准：比较结果为 `True`。

**独立：** 解释为什么两个 tokenizer 对同一句话可能返回长度不同的 ID 序列。提示：词表以及训练算法不同。

**迁移：** 某新模型经 tokenizer 编码后序列长度暴涨，列出三项检查：确认所载入的 tokenizer 与模型版本配对；核对是否加载了正确词表/附加 token；统计文本里是否有罕见字符导致 byte fallback。不能仅把新 ID 直接塞进旧模型的 embedding。

> [!example]- 参考答案与解析
> 跟做可写为 `text = "中文猫🙂"; assert decode_ids(encode_text(text)) == text`。assert 成立时不输出，失败会报错。
>
> 不同 tokenizer 的词表和切分规则不同，同一字符串可能是一个长词 token、若干子词 token，或多个字节 token。ID 数量不同不表示文字不同。
>
> 搭配检查要同时核对 tokenizer 文件、模型配置和 special-token 映射；embedding 的行数必须能接收 token ID。换词表但沿用旧模型权重会让 ID 的含义对不上。

下一步先完成 [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/02 亲手训练字节BPE并编码新文本|BPE 训练与编码详细课]]，亲手数频次、保存规则、处理未见文本；之后再回到模板课。补充课的 ID 与本页不同，不可混用。

## 本讲完成检查

- [ ] 能用自己的话说明文本→token→ID 的顺序。
- [ ] 能区分 BPE 的合并思路、Unigram 的概率/删词思路和 SentencePiece 工具。
- [ ] 能解释教学字节回退为何保证文本可还原、为何不是生产 tokenizer。

> [!nav] 路线续读
> 若本讲已到当前路线列出的范围末尾，返回原阶段继续下一项或检查产物；继续单元学习时沿下方“下一讲”。
>
> - [[00_学习路线/02 学习Agent与RAG应用#阶段 5：审计、安全与整合|学习Agent与RAG应用 · 阶段 5：审计、安全与整合]]

## 继续学习

> [!next] 下一步
> [[01_学习指南/10_Tokenizer对话模板与训练样本/逐讲学习/02 亲手训练字节BPE并编码新文本|下一讲：亲手训练字节BPE并编码新文本]]

> [!info]- 练习与记录
> [[01_学习指南/10_Tokenizer对话模板与训练样本/示例工程/README#代码导航|查看源码]] · [[01_学习指南/10_Tokenizer对话模板与训练样本/示例工程/README#运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 10：Tokenizer、对话模板与训练样本|本单元完成清单]]
