---
title: 单元 13 参考工程验证记录
tags: [validation, rag, author-record]
updated: 2026-10-11
cssclasses: ["guide-page", "guide-reference"]
---

# 单元 13 参考工程验证记录

> [[01_学习指南/13_RAG检索重排与评估/00 RAG 检索重排与评估学习地图|学习地图]] · [[01_学习指南/13_RAG检索重排与评估/示例工程/README|代码导航]]

本页记录作者运行，不代表学习者已经完成。数据是合成夹具，结果不能外推真实中文知识库质量。

## 环境与命令

Windows共享 `.venv`，Python3.13.12、scikit-learn1.9.1、NumPy2.5.3、pytest8.4.2、ruff0.16.9；CPU运行。没有安装/升级依赖。

在本单元示例工程执行：

```powershell
..\..\..\.venv\Scripts\python.exe -m ruff check .
..\..\..\.venv\Scripts\python.exe -m ruff format --check .
..\..\..\.venv\Scripts\python.exe -m pytest -q tests
..\..\..\.venv\Scripts\python.exe demo.py
..\..\..\.venv\Scripts\python.exe demo.py --top-k 1 --output results_k1
..\..\..\.venv\Scripts\python.exe demo.py --dimensions 4 --output results_dim4
```

## 实际结果

- 22个测试通过：覆盖分组、权限、改写/RRF、未知词拒答、参数边界、手算指标、失败阶段和dev/test约束。
- Ruff规则检查通过；格式经统一后通过。检查只限定本次工程，没有宣称全仓库全部通过。
- 默认测试集30题含24可答、6无答案。BM25 Recall@3=0.875、MRR=0.729、nDCG=0.766、整体答案正确率0.900；LSA分别0.792/0.694/0.719/0.833；hybrid为1.000/0.938/0.954/1.000；规则rerank为1.000/1.000/1.000/1.000。
- 默认dev选出的阈值均0.0。这不是通用最优阈值，只说明当前目标和夹具不奖励更高阈值。
- 默认无答案正确拒答率均1.000；hybrid/rerank覆盖0.800、可答误拒率0。
- 故意放过未知词的反例忠实度代理1.000，但无答案正确拒答率0.833：premium限定没有证据。
- K=1时BM25/LSA Recall@1均0.625，hybrid0.875，rerank1.000；4维LSA Recall@3降到0.417，其他条件固定。只说明当前夹具的压缩/候选敏感性。
- 语料SHA256：`d91e5480fec8cc0d20be0e153984add763244924da70f8bf6973907fa03e9d4a`；问题SHA256：`9bc01d3558e7dd98ad8a323efeae131cfaeab82f3c0b8be94e926df397a96bfb`。

K/维度变化的输出各自保留在生成目录，不能据小合成集选择生产参数。生成结果被工程 `.gitignore` 忽略，固定语料、问题、代码和参数仍可重跑。

## 运行提示与边界

当前Windows解释器启动打印 `Failed to find real location of C:\Program Files\Python313\python.exe`，但上述命令继续运行并返回实际结果；测试和脚本退出码成功。未改动系统Python。终端中文首次使用默认编码显示乱码，设置 `PYTHONIOENCODING=utf-8` 后正确显示；JSON始终明确UTF-8写入。

无神经Embedding、CrossEncoder、真实LLM、ANN或云向量库；LSA是实际稠密矩阵计算，规则重排依赖人工结构字段。引用定位是合成逻辑定位；身份/租户隔离未实现真实认证。忠实度仅原文子串代理。无答案白名单仅适用于有限词汇，不能推广到任意问题。

教材结构、YAML、内部链接和源码路径使用根 `scripts/check_guide.py` 检查：本单元9份文档、首页/README/三份索引记录以及上一单元两个反向入口共16份，0问题。检查器验证文件目标和标题，不替代Obsidian视觉检查；本轮未打开Obsidian阅读视图逐页查看。
