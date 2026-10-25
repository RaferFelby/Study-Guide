---
title: 测试与实验复现示例工程
aliases:
  - reprokit 示例工程
tags:
  - python
  - testing
  - reproducibility
status: verified
updated: 2026-10-25
cssclasses: ["code-readme", "guide-page", "guide-code"]
---

# 测试与实验复现示例工程

> [!nav] 页面导航
> [[01_学习指南/02_测试与实验复现/00 测试与实验复现学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/02_测试与实验复现/逐讲学习/01 写第一个 pytest 测试|从第一讲开始：写第一个 pytest 测试]]


这是一个不访问网络的最小 Python 工程。它模拟“读取工单、调用工具、解析工具返回的 JSON、运行一个带随机性的实验”，专门用来练习测试和复现。文档在 Obsidian 阅读；源码和配置链接交给 VS Code 打开。

## 安装与一键检查

需要 Python 3.11+。先按仓库根目录 README 准备共享 `.venv`。在本目录的 PowerShell 中执行：

```powershell
..\..\..\.venv\Scripts\python.exe -m pip install --no-build-isolation -e .
..\..\..\.venv\Scripts\python.exe -m pytest -q
..\..\..\.venv\Scripts\python.exe -m ruff check .
..\..\..\.venv\Scripts\python.exe -m ruff format --check .
..\..\..\.venv\Scripts\python.exe -m reprokit.experiment --seed 7 --data-version demo-v1 --output results/run.json
```

最后一条命令会生成 `results/run.json`。同样的种子、数据版本和配置会得到同样的主要结果；时间戳和运行机器信息不要求完全一致。

## 代码导航（VS Code）

1. [data.py](./src/reprokit/data.py)：清洗工单状态并统计数量。
2. [tools.py](./src/reprokit/tools.py)：工具调用协议，以及超时、限流和部分失败的模拟。
3. [output.py](./src/reprokit/output.py)：解析工具返回的 JSON，并拒绝缺字段或错误类型。
4. [experiment.py](./src/reprokit/experiment.py)：固定随机种子，读取版本化数据，保存配置与结果。
5. [test_data.py](./tests/test_data.py)：正常输入、缺字段和未知状态测试。
6. [test_tools.py](./tests/test_tools.py)：用 monkeypatch 模拟超时、限流和部分失败。
7. [test_output.py](./tests/test_output.py)：合法与非法 JSON 测试。
8. [test_experiment.py](./tests/test_experiment.py)：验证同一配置产生相同结果。
9. [pyproject.toml](./pyproject.toml)：pytest、Ruff 和包配置；[requirements-dev.txt](./requirements-dev.txt)：开发工具版本范围。

## 复现边界

- 本工程固定 Python 依赖的大版本范围，但不同操作系统或 Python 小版本可能产生不同的文本细节。
- `random.Random(seed)` 让本示例的抽样过程可重复；真实机器学习实验还需要记录框架、硬件、数据处理代码和模型版本。
- 测试中的 mock 只验证我们设计的故障处理路径，不代表真实服务的所有行为。
- `ruff format --check` 只检查格式；它不能判断业务逻辑正确。
