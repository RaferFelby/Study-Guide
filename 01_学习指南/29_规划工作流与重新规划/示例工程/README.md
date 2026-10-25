---
title: 规划工作流示例工程代码导航
tags: [learning, planning, workflow]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# 规划工作流示例工程代码导航

> [!nav] 页面导航
> [[01_学习指南/29_规划工作流与重新规划/00 规划工作流与重新规划学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/29_规划工作流与重新规划/逐讲学习/01 把业务目标拆成有输入输出的步骤|从第一讲开始：把业务目标拆成有输入输出的步骤]]

## 先运行

VS Code打开本目录，选择根共享解释器：

```powershell
& ..\..\..\.venv\Scripts\python.exe demo.py --output report-my-01.json
```

报告必须是新文件，已存在拒绝覆盖。仅合成政策/工单和标准库线程，无LLM、外网、真实发布或新包。六Case回放固定1/6与16次、串行观察3/6与22次、先规划3/6与23次；模拟恢复4→5次，外部发送始终不存在。真实LLM对照待执行。

## 代码导航

- [workflow.py](./workflow.py)：计划/依赖校验、合成工具、线程调度、有限修复、状态与预算检查点、确认门。
- [demo.py](./demo.py)：六Case策略回放、临时检查点恢复与模拟批准，报告scope明确。
- [scenarios.json](./fixtures/scenarios.json)：正常/主故障/双故障/过期/坏工单/发布待确认六场景。
- [test_workflow.py](./tests/test_workflow.py)：实际并行重叠、修复复用与预算、发布门、恢复匹配、坏计划与对照分母。
- [requirements.txt](./requirements.txt)：运行标准库，测试工具为共享环境已有包。

## 验证与学习导航

```powershell
& ..\..\..\.venv\Scripts\python.exe -m pytest tests -q
& ..\..\..\.venv\Scripts\python.exe -m ruff check .
& ..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

[[01_学习指南/29_规划工作流与重新规划/00 规划工作流与重新规划学习地图|详细六讲]] · [[90_参考与维护/单元验证/29 规划工作流与重新规划验证记录|作者结果]]。模拟批准不是真人授权；检查点只读自己可信文件，不提供防篡改签名或真实副作用恰好一次。失败、等待批准与预算终态都保留，LLM费用为未测，不填0。
