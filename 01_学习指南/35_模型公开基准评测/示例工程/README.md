---
title: README
tags: [learning, benchmark, beginner]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# README

> [!nav] 页面导航
> [[01_学习指南/35_模型公开基准评测/00 模型公开基准评测学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/35_模型公开基准评测/逐讲学习/01 分清公开基准的任务与评分边界|从第一讲开始：分清公开基准的任务与评分边界]]

## 开始阅读

Obsidian 进入 [[01_学习指南/35_模型公开基准评测/00 模型公开基准评测学习地图|学习地图]]；VS Code 从下列代码导航开始。公开归档评分与实际小模型重评分别保存范围，不能混成同一个公开模型成绩。

## 代码导航

- [snapshot.py](./snapshot.py)：显式获取固定提交公开文本、许可证与文件摘要；导入不联网。
- [suite.py](./suite.py)：快照核对、0／few-shot 提示与示范隔离。
- [scoring.py](./scoring.py)：末行数字／选项抽取，区分参考错误与输出格式失败。
- [metrics.py](./metrics.py)：Wilson 区间、同题配对重采样与 pass@k 算式。
- [experiment.py](./experiment.py)：1319 条官方归档独立重算、差异与区间。
- [local_probe.py](./local_probe.py)：隔离进程导入单元 34，加载自己的前后权重实际生成。
- [comparison.py](./comparison.py)：配置相同／不同／未知的对标卡。
- [test_benchmark.py](./test_benchmark.py)：抽取、分母、提示、数据哈希及统计边界验证。
- [requirements.txt](./requirements.txt)：标准库评分与已有 PyTorch 路径说明。
- [manifest.json](./fixtures/manifest.json)：固定提交、URL、字节摘要与示范选择。
- [GSM8K-LICENSE.txt](./fixtures/GSM8K-LICENSE.txt)：随公开数据保留的上游许可证。
- [archive.jsonl](./fixtures/archive.jsonl)：上游完整保存的模型回答，约 2.45 MiB。
- [demos.json](./fixtures/demos.json)：官方训练分区前五条示范。

## 环境与最小运行

所有命令在本单元示例工程 PowerShell 中运行；根共享 `.venv`，不另建环境。公开重放仅标准库；local_probe 用已有 PyTorch，pytest/Ruff 已有。作者 Python 3.13.12、PyTorch 2.14.0+cu130、pytest 8.4.2、Ruff 0.16.9。

```powershell
..\..\..\.venv\Scripts\python.exe experiment.py --output-dir report-my-replay-01
..\..\..\.venv\Scripts\python.exe local_probe.py --weights-dir '../../34_规划与工具使用微调/示例工程/report-my-cpu-01' --device cpu --output-dir report-my-local-cpu-01
..\..\..\.venv\Scripts\python.exe -m pytest -q
..\..\..\.venv\Scripts\python.exe -m ruff check .
..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

所有输出目录须新建、不覆盖。local_probe 先需要按单元 34 教程实际产生 base.pt、tool_only.pt；改为 --device cuda 并换结果目录可验证可用 CUDA。其 import 路径只在该独立进程选择单元 34，不将多个同名模块目录同时放入全局 PYTHONPATH。

公开快照已保存，离线运行即可。需要核对上游时 `snapshot.py --output-dir snapshot-check-01` 下载固定提交文本，每文件最多 16 MiB；不替换原 fixtures，不下载模型或安装依赖。运行脚本前不必安装 datasets、transformers 或评测框架。

## 输出与判定

公开重放生成 report.json 与 0／2-shot Prompt 演示；两组官方归档名 6b_finetuning、6b_verification，均 n=1319，格式失败仍计入分母；本次抽取器与归档标签一致。原始生成配置未知项保持 null，教学提示不是原模型提示。

local_probe 生成独立报告，记录权重、任务、代码哈希及 CPU/CUDA、FP32、greedy、8 新 token；三个推理 seed 重复，非独立训练或真实公开题库推理。HumanEval 不执行代码，仅验证组合统计；未安装 lm-evaluation-harness，也没有自然语言大模型现场生成或真实量化实验。

实际分数、统计假设与未测范围见 [[90_参考与维护/单元验证/35 模型公开基准评测验证记录|作者验证]]。新增学习脚本与个人报告由学习者自己记录，作者结果不修改个人勾选。
