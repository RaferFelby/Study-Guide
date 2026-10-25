---
title: 第 2 讲：用父子 Span 追踪模型与工具
tags: [lesson, tracing, span]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 2 讲：用父子 Span 追踪模型与工具

> [!nav] 页面导航
> [[01_学习指南/20_可观测性可靠性与成本/00 可观测性可靠性与成本学习地图#学习顺序|单元 20：可观测性可靠性与成本]] · [[01_学习指南/20_可观测性可靠性与成本/逐讲学习/01 用结构化日志记录一次任务|上一讲]] · [[01_学习指南/20_可观测性可靠性与成本/逐讲学习/03 把事件汇成指标与离线仪表盘|下一讲]]

## 本讲任务与前置

一份退款任务调用缓存、检索工具和模型，失败发生在哪一步？只凭时间相近的日志容易串错任务。复习with/异常与单元14轨迹，本讲用trace_id和父子span建立明确关联。

## Span是什么

Span是一段有开始/结束、状态和属性的操作，例如一次模型调用。Trace是一组同任务相关span。每个span有自己的span_id；parent_span_id指向调用它的步骤；同trace_id把整棵树关联起来。[OpenTelemetry的trace说明](https://opentelemetry.io/docs/concepts/signals/traces/)提供标准概念，当前工程只是简化教学实现，没有兼容SDK导出协议。

父任务包含子调用，像函数调用栈，但跨进程时必须显式传播上下文，不能靠Python列表自动跨网络。时间相同不是亲子关系，ID关系才是。

## 最小示例：可控时钟看清关系

新建`lesson_span.py`：

```python
from telemetry import SimulatedClock, TraceRecorder

clock = SimulatedClock()
recorder = TraceRecorder(clock, timing_kind="simulated")
with recorder.span("task") as parent:
    clock.advance(0.01)
    with recorder.span("tool", {"tool": "search_policy"}) as child:
        clock.advance(0.02)
print(parent["duration_ms"], child["duration_ms"])
print(child["parent_span_id"] == parent["span_id"])
print(child["trace_id"] == parent["trace_id"])
```

代码按缩进执行：先建立时钟，再建立记录器；外层 `with` 打开task，`as parent` 接收该任务的事件字典。advance先增加0.01秒；进入内层tool时，`as child` 接收工具事件，再增加0.02秒。内层结束时先计算工具20ms，外层结束时计算累计30ms。秒转毫秒乘1000，父任务覆盖子任务这段时间。

`{"tool": "search_policy"}` 是属性字典，不是调用search_policy；本例只记录名为tool的模拟过程。`==` 比较两值相等，输出True/False，不会修改ID。span_id由记录器生成，每次运行不同；不要把随机ID写死进预期输出。

预期30.0、20.0，两比较True。advance只把合成时钟数值增加，没有真的sleep20毫秒。timing_kind=simulated明确记录来源；真实测量用TraceRecorder默认perf_counter，但不能从本脚本推测性能。

## contextmanager逐步解释

telemetry.span使用@contextmanager让生成器函数成为with可用对象。进入with前创建事件、取开始时刻、压入active_spans；yield把事件交给with块；块退出后finally算耗时、弹出栈并追加事件。不是每一行都需要装饰器，只有“进入/退出都要处理”的职责适合这里。

异常会标status=error、error_type，随后raise继续向调用者传播；finally依然收尾。日志不能把失败吞掉让业务继续装成功。因为事件在完成时追加，子span常排在父span前，读取JSONL不能把第一行假定为根。

当前active_spans是每个串行recorder的列表，不能由并发线程共享。真实多协程/跨线程需上下文局部状态和传播机制，或使用成熟遥测SDK；不要机械把这个列表放进单元18多线程服务。

## 动手：沿一条trace找模型与工具

先运行demo输出报告。新建`lesson_trace_read.py`：

```python
import json
from pathlib import Path

path = Path(__file__).parent / "report-01" / "baseline-trace.jsonl"
events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
root = next(event for event in events if event["parent_span_id"] is None)
related = [event for event in events if event["trace_id"] == root["trace_id"]]
for event in related:
    print(event["name"], event["duration_ms"], event["parent_span_id"])
```

这段先将文件拆成行，每行 `json.loads` 后组成 `events` 列表。列表推导式 `[处理表达式 for 项 in 列表]` 等价于逐条循环并追加结果；带 `if` 的形式只保留满足条件的项。`next(生成器)` 取第一个匹配事件；若没有根会抛 `StopIteration`，应检查读的是本例报告、文件是否完整，而不是随便取第一行。

`is None` 判断是否为空父ID；`related` 按同一trace筛选，避免混入其他任务。最后for逐条打印事件名、耗时与父ID。你也可以先用普通循环逐行展开这些步骤，理解后再读紧凑写法。

第一次任务通常有cache_lookup 5ms、tool100ms、model200ms、task305ms；所有耗时均合成。同一任务超时则没有modelspan，因为工具失败后没调用模型；缓存命中任务没有tool/model，不应伪造调用。

parent_span_id为空的根是任务级窗口，其他span父ID对应根。随意挑另一trace的model拼到这份任务会产生错误归因，脚本用ID筛选保证不串。

## 时间与成本不要双重计数

task305ms已经包含子span5+100+200；把根和子全加起来得到610ms是重复计算。本串行案例子时间恰好相加，未来并行时子span可重叠，总任务时长也不等于所有子时长之和。

同理根cost_units是任务总账，modelspan成本是组成项。汇总任务指标只用每任务结果/根，不将所有事件成本一起加。下一讲的summary从rows读取一份任务记录。

## 常见错误

- 看不到root在第一行：span完成才写，按parent为空找根。
- 跨线程共享一个recorder产生乱亲子：当前实现限定串行，每请求独立或改成熟上下文传播。
- 工具超时后仍期待modelspan：执行并未到模型，缺span本身是路径证据。
- 把模拟时钟看成真实耗时：看timing_kind，实际perf_counter例子需单独测量。

## 练习与答案

跟做：选一条trace画出task→cache/tool/model关系。完成判断：父ID实际匹配且根耗时只计一次。

独立：两个并行工具各100ms，任务大约110ms，能否按工具相加报告200ms任务耗时？

迁移：为HTTP提交→异步工作线程设计request_id/job_id/trace_id关系，并说明跨线程要传什么。

> [!example]- 参考答案与解析
> 工具耗时合计200ms可表述为累计调用时间，但墙上任务耗时约110ms；它们用途不同。
>
> 提交请求有自己的请求trace；持久job_id关联异步工作run/trace与之后轮询请求。工作任务可用link关联提交trace，或规范传播父上下文；不能因为共享进程就依赖全局列表自动关联。ID来源需服务可信生成/校验。

## 本讲完成后

能沿单次任务追踪调用和失败，再把很多任务汇成指标。

## 继续学习

> [!next] 下一步
> [[01_学习指南/20_可观测性可靠性与成本/逐讲学习/03 把事件汇成指标与离线仪表盘|下一讲：把事件汇成指标与离线仪表盘]]

> [!info]- 练习与记录
> [[01_学习指南/20_可观测性可靠性与成本/示例工程/README#代码导航|查看源码]] · [[01_学习指南/20_可观测性可靠性与成本/示例工程/README#运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 20：可观测性、可靠性与成本|本单元完成清单]]
