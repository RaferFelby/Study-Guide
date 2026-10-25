---
title: 单元 15 示例工程导航
tags: [code, tools, protocol]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# 单元 15 示例工程

> [!nav] 页面导航
> [[01_学习指南/15_工具调用协议与工具设计/00 工具调用协议与工具设计学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/15_工具调用协议与工具设计/逐讲学习/01 为一个只读工具写清输入输出|从第一讲开始：为一个只读工具写清输入输出]]

两个教学工具：读取虚构政策、创建内存演示工单。输入采用明确Schema子集；执行器校验可信context、参数、确认和幂等。内部消息按call_id关联，不连接真实模型/供应商API。

## 运行

在本目录VS Code PowerShell终端用共享环境：

```powershell
..\..\..\.venv\Scripts\python.exe demo.py
..\..\..\.venv\Scripts\python.exe -m pytest -q tests
..\..\..\.venv\Scripts\python.exe -m ruff check .
..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

预期确认前confirmation_required，确认后DEMO-1，重复请求同ID，实际工单数1；四题规则选择准确率1、参数准确率0.75、任务完成率0.75。`demo.py`主动构造批准仅用于虚构内存演示。

## 代码导航

- [contracts.py](./contracts.py)：工具说明/Schema、调用/上下文类、严格JSON解析和扁平校验子集。
- [runtime.py](./runtime.py)：权限、查询、批准指纹、内存写入与幂等作用域。
- [messages.py](./messages.py)：请求消息、执行回传、pending ID消费与通用结果外壳校验。
- [evaluation.py](./evaluation.py)：四条固定任务与不使用gold的规则选择器。
- [demo.py](./demo.py)：一轮消息、确认/重复和三层指标。
- [test_tools.py](./tests/test_tools.py)：解析/类型/范围、权限、确认、缓存/冲突、关联与评估边界。
- [requirements.txt](./requirements.txt)：标准库运行，复用共享开发工具。

## 契约与限制

成功：ok=true、data对象、error=null；失败：ok=false、data=null、error含code/message/retryable。空证据是成功查询。返回摘要保留匹配数量及截断标志。

Schema不是完整验证库，输出仅验证外壳；生产按工具建立输出Schema。内存幂等不防并发/崩溃/重启；fingerprint不是批准签名；context无真实认证。工具消息是内部概念格式，需要单独供应商适配。政策定位是逻辑标签，非实际文件。四题是流程探针，非模型质量基准。

[[01_学习指南/15_工具调用协议与工具设计/00 工具调用协议与工具设计学习地图|单元 15：工具调用协议与工具设计]]。
