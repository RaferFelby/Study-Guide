---
title: README
tags: [learning, tool-training, beginner]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# README

> [!nav] 页面导航
> [[01_学习指南/34_规划与工具使用微调/00 规划与工具使用微调学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/34_规划与工具使用微调/逐讲学习/01 把工具任务拆成计划调用观察与答案|从第一讲开始：把工具任务拆成计划调用观察与答案]]

## 从哪里开始

教材入口 [[01_学习指南/34_规划与工具使用微调/00 规划与工具使用微调学习地图|学习地图]]。Obsidian 读解释，VS Code 读下列源码。此工程实际训练微型 GRU 生成计划／工具／对象，调用固定只读工具，再根据真实观察生成答案。没有外部 API、任意命令执行或模型下载。

## 代码导航

- [tools.py](./tools.py)：允许的工具、调用解析、语义检查、只读目录。
- [data.py](./data.py)：合成任务、错误注入与隔离、拒答、重放、输入标签。
- [model.py](./model.py)：66 token 词表对应的 17154 参数 GRU 与限长生成。
- [training.py](./training.py)：只监督模型输出的全批次 SFT。
- [evaluation.py](./evaluation.py)：模型动作→校验→执行→观察→模型答案与探针。
- [experiment.py](./experiment.py)：相同 Base 的两个分支、权重与报告。
- [test_tool_training.py](./test_tool_training.py)：数据、监督边界、执行错误与 CPU/CUDA 更新检查。
- [requirements.txt](./requirements.txt)：最小依赖说明，版本实测见作者记录。

## 环境与运行

所有命令在本“示例工程”目录的 PowerShell 中运行，使用工作区共享环境。作者 Python 3.13.12、PyTorch 2.14.0+cu130、pytest 8.4.2、Ruff 0.16.9。依赖已存在；需要变更时按工作区安装审批执行，不在单元新建环境。

```powershell
..\..\..\.venv\Scripts\python.exe experiment.py --device cpu --output-dir report-my-cpu-01
..\..\..\.venv\Scripts\python.exe experiment.py --device cuda --output-dir report-my-cuda-01
..\..\..\.venv\Scripts\python.exe -m pytest -q
..\..\..\.venv\Scripts\python.exe -m ruff check .
..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

CUDA 命令只在 `torch.cuda.is_available()` 为 True 时使用；CPU 完整覆盖学习流程。`--output-dir` 必须是新目录，旧结果不覆盖。pytest 执行测试；CUDA 更新测试在无 CUDA 时明确跳过，本机作者没有跳过。Ruff 检查代码规范，format --check 只核对格式。

## 输出与指标

52 原始轨迹保留，48 正常轨迹拆为 96 行，加 12 行正确故障拒答；仅工具 108 行，重放分支 116 行。旧复述 Base 100 次更新，两工具分支各 200 次更新，FP32 全参数 SFT，非 LoRA／DPO。每个结果目录包含 base.pt、tool_only.pt、with_replay.pt、raw_traces.jsonl、report.json。

报告逐项保留动作、观察、答案、执行次数和状态，所有正常层次计数分母为 12。案例组切分不重合但对象与模板重用；变化目录、工具不可用、两条旧复述、未训练 shape 工具和 item-6 对象单独检查。权重用于推理，不支持等价续训。

## 范围

固定 token 语法不是完整 JSON／MCP 协议，短计划不代表多步规划，宿主掌握结构化意图并先拒绝错误语义。真实神经模型生成动作与答案，宿主不改错动作或代填最终答案。没有自动工具发现、真实自然语言对话基准、外部工具授权或公开盲测。实际收益与失败见 [[90_参考与维护/单元验证/34 规划与工具使用微调验证记录|作者验证记录]]。
