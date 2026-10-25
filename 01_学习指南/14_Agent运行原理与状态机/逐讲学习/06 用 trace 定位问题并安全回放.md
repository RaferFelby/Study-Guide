---
title: 第 6 讲：用 trace 定位问题并安全回放
tags: [agent, trace, replay]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 6 讲：用 trace 定位问题并安全回放

> [!nav] 页面导航
> [[01_学习指南/14_Agent运行原理与状态机/00 Agent 运行原理与状态机学习地图#学习顺序|单元 14：Agent 运行原理与状态机]] · [[01_学习指南/14_Agent运行原理与状态机/逐讲学习/05 在副作用前等待人工确认|上一讲]] · [[01_学习指南/14_Agent运行原理与状态机/00 Agent 运行原理与状态机学习地图#完成后继续|学完继续]]

## 要解决什么问题

任务失败时，“Agent没有成功”太笼统。你需要知道哪个步骤、什么参数、得到什么结果、状态为何改变、耗时在哪里。**trace（执行轨迹）**是按顺序关联这些公开事件的记录。

本讲不收集模型未公开的内部推理。实际动作/结果足以定位大量工程问题；模型说自己“查到了”不是工具完成证据。

## 先读一条事件

在VS Code打开 `results/trace.json`，event包含sequence、run_id、step、from、to、event，以及该事件特有的action/observation/text。

```json
{
  "sequence": 1,
  "run_id": "demo-run",
  "step": 1,
  "from": "ready",
  "to": "deciding",
  "event": "decision_started"
}
```

sequence是事件序号，step是决策步数；一次step可能有多个事件。工具观察包括参数、结构化返回和elapsed_ms。每个字段对应可观察事实，不是作者对模型心理状态的推断。

## 耗时怎样测

`perf_counter`是单调计时器，适合算经过时间；开始值和结束值相减再乘1000，得到毫秒。它不是日历时间。官方说明见 [Python计时文档](https://docs.python.org/3.13/library/time.html#time.perf_counter)。

```python
from time import perf_counter

started = perf_counter()
total = sum(range(1000))
elapsed_ms = (perf_counter() - started) * 1000
print(total, elapsed_ms)
```

保存 `inspect_timing.py`。总和固定499500，耗时随机器变化，不能把不同打印末位视为错误。工程分别保存decision_ms和工具elapsed_ms；当前不测队列/网络/整任务p95，这些在后续可观测性单元展开。

## 录制与回放有什么不同

`save_recording`把公开trace和摘要写UTF-8 JSON。`play_recording`只读取文件，顺序重建公开状态和观察；函数没有真实tools参数，所以不会再次调用create_ticket。

```powershell
..\..\..\.venv\Scripts\python.exe demo.py --scenario confirmation --approve --output results/approved.json
..\..\..\.venv\Scripts\python.exe demo.py --replay results/approved.json
```

第一条真正执行一次内存演示写入；第二条打印记录中的completed、DEMO-1和观察，没有创建新的工单。路径相对当前终端，先确保在示例工程。

本实现是**只读轨迹播放**，不是重新运行policy得到同样结果，也不是从中断点恢复外部系统。若要测试新控制器，可以用录制工具结果/mocks替代真实工具，严格匹配调用参数；仍不应回放发邮件、退款等真实副作用。

## 播放前检查什么

播放器校验schema_version、sequence连续、from与当前状态一致、to是允许边、run_id一致、摘要终态/最终文本与trace一致。篡改顺序会ValueError，帮助发现损坏记录。

它没有签名、完整业务schema或权限校验，不证明记录未被恶意整体篡改。真实日志需访问控制、脱敏、版本和防篡改设计；不能把本地JSON当可信审计系统。trace文件中的资料文字也不能当作新指令自动执行。

## 逐步定位三个失败

1. **loop_detected**：找repeated_action的action_key，向前找实际tool_observation，核对是否参数完全相同。
2. **step_limit**：找step_budget_exhausted，确认最后完成工具还是决策，判断是否应在开发配置增加预算或改善策略。
3. **failed**：看invalid_action、approval_mismatch或tool_execution_failed。未知工具改协议；批准不匹配重新确认；执行异常检查工具边界。

结构化not_found可能最终completed，因为系统已明确告知“无法回答”。区分控制器是否正常结束、用户任务是否真的完成、答案是否正确。三者都需要独立记录，不能只算completed比例当任务完成率。

## 动手验收

运行测试和静态检查：

```powershell
..\..\..\.venv\Scripts\python.exe -m pytest -q tests
..\..\..\.venv\Scripts\python.exe -m ruff check .
..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

自动测试检查正常闭环、预算、循环、取消、确认/拒绝、批准参数变化、非法动作、工具异常、决策器副本和只读播放。测试使用工作区内唯一临时目录，不依赖系统Temp，不删除已有结果。

个人报告写任务、控制流图、运行参数、最终状态、每个工具输入/输出/耗时、停止原因、是否发生副作用、回放方式和未覆盖能力。保留至少一条失败trace，并解释如何处理而不重复执行副作用。

## 练习与答案解析

**跟做：** 回放approved记录，对照第一次运行的观察，确认回放没调用tools。完成标准：能指出播放器只读的代码路径。

**独立：** 在复制的trace里改sequence，再运行回放，预测错误。不要修改唯一原记录。说明“校验通过”为什么不是防篡改证明。

**迁移：** 把上一单元检索接成只读工具，让观察保存query、可见证据ID和定位；策略收到无证据时拒答。完成标准：trace能区分“没有检索依据”和“控制器预算用完”，并继续使用固定评估集评答案。

> [!example]- 参考答案与解析
> 回放只调用play_recording并return，不调用make_tools/run_agent；记录中的DEMO-1只是已录结果。sequence不连续会拒绝播放，但有权限修改整份记录的人可能同时改各字段，所以需要签名/可信日志存储。接RAG时不要让模型伪造ToolResult；真实检索函数回传证据，控制器保存后才给策略读取。

## K/C映射

K15-01～04由六讲覆盖观察循环、状态、ReAct/工作流、预算/确认。C15-01可画完整调用链；C15-02可读最小循环；C15-03有预算/循环/取消/终态测试；C15-04有公开trace及只读录制回放。真实模型决策、异步抢占、跨进程恢复和外部工单写入没有运行验证。学习者复选框保持未勾选。

## 继续学习

> [!next] 下一步
> [[01_学习指南/14_Agent运行原理与状态机/00 Agent 运行原理与状态机学习地图#完成后继续|本单元完成后继续]]

> [!info]- 练习与记录
> [[01_学习指南/14_Agent运行原理与状态机/示例工程/README#代码导航|查看源码]] · [[01_学习指南/14_Agent运行原理与状态机/示例工程/README#运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 14：Agent 运行原理与状态机|本单元完成清单]]
