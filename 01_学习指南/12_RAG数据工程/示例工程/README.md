---
title: 单元 12 示例工程导航
tags:
  - code
  - rag
  - data-engineering
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# 单元 12 示例工程

> [!nav] 页面导航
> [[01_学习指南/12_RAG数据工程/00 RAG 数据工程学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/12_RAG数据工程/逐讲学习/01 清洗 PDF 网页与表格文本|从第一讲开始：清洗 PDF 网页与表格文本]]

这个标准库教学工程读取本地 Markdown、HTML 和 CSV fixture，构建切块，存入 SQLite，演示版本更新、权限过滤、删除和引用返回。它不下载模型、不连接外部向量库、不生成答案。检索采用词面词项重叠，是透明的教学基线，不是语义向量召回。

## 运行

在 VS Code 打开本目录，在 PowerShell 终端中运行：

```powershell
..\..\..\.venv\Scripts\python.exe demo.py
..\..\..\.venv\Scripts\python.exe -m pytest -q tests
..\..\..\.venv\Scripts\python.exe -m ruff check .
```

`demo.py` 使用临时目录放 SQLite 文件，程序退出后自动清理。运行差异主要是文件路径和 SQLite/ Python 版本；示例 query 的命中由固定夹具决定。

## 代码导航

- [ingestion.py](./ingestion.py)：TXT/Markdown 段落、HTML 可见文字、CSV 行解析与基础空白清洗；CSV 权限列会保留为该行访问标签。
- [chunking.py](./chunking.py)：带 overlap 的固定字符窗口和保留来源/权限边界的结构切块。
- [knowledge_base.py](./knowledge_base.py)：SQLite schema、摘要去重、事务替换、权限过滤、词面探针、引用结果和级联删除。
- [demo.py](./demo.py)：三条固定 query 对照、引用打印、未变检测、权限改版、CSV 行级权限和删除演示。
- [fixtures](./fixtures)：本地 Markdown、HTML、CSV 教学数据，不含个人信息。
- [test_ingestion.py](./tests/test_ingestion.py)：解析/清洗正常路径与不支持类型。
- [test_chunking.py](./tests/test_chunking.py)：窗口边界、overlap 和结构定位。
- [test_knowledge_base.py](./tests/test_knowledge_base.py)：不变跳过、版本替换、ACL、删除和参数边界。
- [requirements.txt](./requirements.txt)：本单元本地工程的最小依赖说明；无需新增运行依赖。

## 数据与教学限制

SQLite 中 `permission` 是演示标签；生产环境不能信任用户自行声明标签作为授权。示例切块按字符计数，真实模型应使用对应 tokenizer 管理 token 长度。本文工程不含 PDF/OCR adapter，也不含 sentence embedding 或 ANN 索引，避免把未安装、未运行的能力写成已验证功能。
