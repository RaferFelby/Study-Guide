---
title: 单元 20 示例工程导航
tags: [code, observability, cost]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# 单元 20 示例工程

> [!nav] 页面导航
> [[01_学习指南/20_可观测性可靠性与成本/00 可观测性可靠性与成本学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/20_可观测性可靠性与成本/逐讲学习/01 用结构化日志记录一次任务|从第一讲开始：用结构化日志记录一次任务]]

标准库离线原型：24合成请求×5策略，父子span/JSONL、指标/P95、模拟usage/虚构Decimal账本、用户知识版本缓存、模型路由/错误裁剪、SLO文本动作、离线HTML报告。无真实模型/监控服务。

## 运行

本目录VS Code终端使用工作区根共享环境：

```powershell
..\..\..\.venv\Scripts\python.exe demo.py --output-dir report-01
..\..\..\.venv\Scripts\python.exe -m pytest -q tests
..\..\..\.venv\Scripts\python.exe -m ruff check .
..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

目录已存在时拒绝覆盖，改report-02；不用安装新包。报告含dashboard.html、report.json、各策略trace.jsonl。源码/数据VS Code阅读，教材Obsidian；离线HTML可浏览器查看，不启动网络服务。

baseline可用20/24、质量24/24、P95模拟305ms、usage1024/708、虚构成本2.680；cached1.360、routed1.6048、合用0.8224且质量不变；bad_crop2.480但质量16/24。缓存命中10；四超时不缓存；全部是夹具，不是实际token/性能/费用。

## 代码导航

- [telemetry.py](./telemetry.py)：串行父子span、异常重抛、标量白名单/再次检查、JSONL拒覆盖。
- [workload.py](./workload.py)：正常/VIP/冲突/超时的固定12题重复，共24。
- [pipeline.py](./pipeline.py)：模拟时钟/模型usage、用户版本缓存32项、路由/坏裁剪。
- [costs.py](./costs.py)：虚构费率版本、Decimal校验/计算、基础设施分摊最小函数。
- [reporting.py](./reporting.py)：分母/P95nearest-rank、联合SLO窗口、转义HTML。
- [demo.py](./demo.py)：固定集实验与报告；gold不传pipeline。
- [test_observability.py](./tests/test_observability.py)：trace、隐私字段、成本/优化质量、缓存隔离、分位/SLO和HTML边界。
- [requirements.txt](./requirements.txt)：运行仅标准库，pytest/Ruff复用共享环境。

## 边界

recorder仅串行，不是并发上下文或OpenTelemetry导出；未实现SDK/采样/平台/线上告警。白名单不识别所有秘密，代码仍需审查。usage是假供应商字节计数，不是真tokenizer；费率非实际币种；基础设施未并入demo总额。缓存限当前实验窗口，无TTL/持久化/多进程共享。SLO仅文本决策，无真实灰度/部署回滚。

[[01_学习指南/20_可观测性可靠性与成本/00 可观测性可靠性与成本学习地图|返回地图]]。
