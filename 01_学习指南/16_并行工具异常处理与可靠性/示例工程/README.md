---
title: 单元 16 示例工程导航
tags: [code, asyncio, reliability]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# 单元 16 示例工程

> [!nav] 页面导航
> [[01_学习指南/16_并行工具异常处理与可靠性/00 并行工具与可靠性学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/16_并行工具异常处理与可靠性/逐讲学习/01 从顺序等待走到异步并行|从第一讲开始：从顺序等待走到异步并行]]

标准库异步调度：有界并发、同批安全请求共享、每次超时、限次退避、启动速率、简化熔断、部分结果、冲突和长输出引用。不连接外部服务。

## 运行

在本目录VS Code终端：

```powershell
..\..\..\.venv\Scripts\python.exe demo.py
..\..\..\.venv\Scripts\python.exe -m pytest -q tests
..\..\..\.venv\Scripts\python.exe -m ruff check .
..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

预期串行和并发各成功3/3，时间因平台不同；冲突与unknown_tool保留；长输出有引用，可回查完整900字符。作者沙箱中事件循环的socketpair停滞，沙箱外同共享环境检查通过，见验证记录。

## 代码导航

- [scheduler.py](./scheduler.py)：Request/ToolSpec、限流异常、简化CircuitBreaker、批调度/重试/清理、摘要回查和事实聚合。
- [demo.py](./demo.py)：串并行对照、冲突/部分失败、超长结果。
- [replanning.py](./replanning.py)：按结构错误提出规则下一步，不自动执行新的副作用。
- [test_replanning.py](./tests/test_replanning.py)：未知写入、参数错误、限流/熔断、超时与摘要决策。
- [test_scheduler.py](./tests/test_scheduler.py)：峰值/顺序、同批重复、读写超时、限流、熔断、依赖、取消和结果预算。
- [requirements.txt](./requirements.txt)：只用标准库，共享pytest/ruff。

## 关键约定

新工具默认不可安全重试，必须由可信注册显式标只读或真实幂等。max_attempts包含首次。Retry-After超等待预算停止，不提前打上游。每次工具超时不含排队/退避；协作取消不强杀阻塞工具。非幂等写超时结果未知，不盲重试。

同批共享假定同授权范围，无跨批缓存。熔断冷却后直接重开，无半开探针。启动间隔单进程共享，速率等待会占并发槽；无分布式限流/流式队列。完整结果只内存，无权限/TTL/容量生产实现。preview为文本，可能是半JSON，不能解析为完整结果。

[[01_学习指南/16_并行工具异常处理与可靠性/00 并行工具与可靠性学习地图|单元 16：并行工具与可靠性]]。
