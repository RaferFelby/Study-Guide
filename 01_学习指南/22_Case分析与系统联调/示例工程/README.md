---
title: 单元 22 示例工程导航
tags: [code, integration, case]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# 单元 22 示例工程

> [!nav] 页面导航
> [[01_学习指南/22_Case分析与系统联调/00 Case分析与系统联调学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/22_Case分析与系统联调/逐讲学习/01 把失败记录成可复现 Case|从第一讲开始：把失败记录成可复现 Case]]

五合成失败+三回归：同义检索、工具参数、围栏解析、owner授权、暂时只读失败。七配置对照，每单变量只修一Case，组合重跑端到端。baseline故意缺授权只用于虚构常量，不可接真实数据。

## 运行

本目录VS Code终端使用根共享环境：

```powershell
..\..\..\.venv\Scripts\python.exe experiments.py --output report-01.json
..\..\..\.venv\Scripts\python.exe -m pytest -q tests
..\..\..\.venv\Scripts\python.exe -m ruff check .
..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

报告已有拒绝覆盖，改新名。baseline3/8，各单项4/8，组合8/8，均无正常回归退步；工具尝试6→8；实际读取前核owner，持续故障2次终止；耗时perf_counter实测夹具函数，不是生产模型性能。

## 代码导航

- [cases.py](./cases.py)：输入/gold/作者根因与严重度，五失败/三正常。
- [contracts.py](./contracts.py)：冻结配置、最多2只读尝试、明确异常类型。
- [tools.py](./tools.py)：虚构账户读、参数/owner校验、合成暂时故障。
- [parsing.py](./parsing.py)：纯JSON或约定完整围栏，字段/类型取值检查。
- [pipeline.py](./pipeline.py)：阶段事件、实际读计数、错误传播与有限安全重试。
- [experiments.py](./experiments.py)：replace单变量、逐ID对比、SHA与报告。
- [test_integration.py](./tests/test_integration.py)：实验差异/回归、权限在读前、持续失败/解析边界。
- [requirements.txt](./requirements.txt)：标准库运行，测试工具复用共享环境。

## 范围限制

无真实LLM/Agent框架/网络故障/客户事故；作者标注未独立人工审核。Settings默认是故意缺陷实验基线，非生产推荐。只读重试无真实退避/总时限，未处理外部写。只展示五根因机制，未全类别/并发/缓存/持久系统实测；合成8/8不证明泛化。

[[01_学习指南/22_Case分析与系统联调/00 Case分析与系统联调学习地图|返回地图]]。
