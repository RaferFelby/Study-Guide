---
title: 单元 13 示例工程导航
tags: [code, rag, evaluation]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# 单元 13 示例工程

> [!nav] 页面导航
> [[01_学习指南/13_RAG检索重排与评估/00 RAG 检索重排与评估学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/13_RAG检索重排与评估/逐讲学习/01 建立带证据的检索评估集|从第一讲开始：建立带证据的检索评估集]]

固定英文合成夹具：24段、60题（48可答、12无答案），dev/test各30题。比较BM25、TF-IDF+SVD的LSA稠密检索、查询改写+多查询+RRF、规则重排。答案使用白名单与原文抽取。无神经Embedding、CrossEncoder、LLM或外部服务。

## 运行

在本目录的 VS Code PowerShell 终端使用共享环境：

```powershell
..\..\..\.venv\Scripts\python.exe demo.py
..\..\..\.venv\Scripts\python.exe -m pytest -q tests
..\..\..\.venv\Scripts\python.exe -m ruff check .
..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

默认输出到脚本同级 `results`；可用 `--output results_k1 --top-k 1` 保留另一组结果。示例CPU运行，使用共享环境已有scikit-learn；不需要额外安装或下载模型。

## 代码导航

- [corpus.json](./fixtures/corpus.json)：24条证据和逻辑定位符。
- [questions.json](./fixtures/questions.json)：答案、证据ID、定位、权限和分组标签。
- [build_fixture.py](./build_fixture.py)：透明的合成夹具构造记录；正常运行不用执行，执行会重写夹具。
- [data.py](./data.py)：数据类、JSON加载、标注一致性检查。
- [retrieval.py](./retrieval.py)：英文分词、BM25、LSA、RRF、规则重排和候选权限过滤。
- [answering.py](./answering.py)：受限问法识别、未知词拒答、阈值、原文字段抽取。
- [evaluation.py](./evaluation.py)：排名指标、答案指标、失败分类和开发集阈值选择。
- [demo.py](./demo.py)：完整实验、逐题JSON和故意关闭保护的反例。
- [test_retrieval.py](./tests/test_retrieval.py)：分组、权限、改写、RRF、拒答和参数边界。
- [test_evaluation.py](./tests/test_evaluation.py)：手算指标、失败阶段、dev/test约束和分母。
- [requirements.txt](./requirements.txt)：本单元依赖约束；工作区的原约束仍见根 requirements-ml.txt。

## 结果怎么读

每个策略文件含 `dev_candidates`、`test_report`、`rows`。排序指标只算可答题；整体答案正确率含正确拒答；覆盖率是所有题中非空回答占比。忠实度是原文子串代理，不能代表完整语义蕴含。`unsafe_baseline.json`故意忽略未知限定词，展示“引用存在仍答错”。

逻辑定位如 `policies/storage.md#retention` 对应JSON中的资料，不是真实磁盘文件。public/staff只是演示标签。候选过滤不代表训练统计、日志和缓存完全租户隔离。数据高度模板化，满分不能外推中文或生产质量。

返回教程：[[01_学习指南/13_RAG检索重排与评估/00 RAG 检索重排与评估学习地图|学习地图]]。
