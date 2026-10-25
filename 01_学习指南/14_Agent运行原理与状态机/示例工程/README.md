---
title: 单元 14 示例工程导航
tags: [code, agent, state-machine]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# 单元 14 示例工程

> [!nav] 页面导航
> [[01_学习指南/14_Agent运行原理与状态机/00 Agent 运行原理与状态机学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/14_Agent运行原理与状态机/逐讲学习/01 看懂观察决策行动反馈循环|从第一讲开始：看懂观察决策行动反馈循环]]

标准库顺序Agent：规则提出动作，控制器校验/执行/记录。两个工具读取本地虚构政策、写入内存工单，均不访问外部服务。决策器写死了演示任务，不能解析任意自然语言。

## 运行

在本目录VS Code PowerShell终端执行：

```powershell
..\..\..\.venv\Scripts\python.exe demo.py
..\..\..\.venv\Scripts\python.exe demo.py --scenario loop --output results/loop.json
..\..\..\.venv\Scripts\python.exe demo.py --scenario limit --output results/limit.json
..\..\..\.venv\Scripts\python.exe demo.py --scenario cancel --output results/cancel.json
..\..\..\.venv\Scripts\python.exe demo.py --scenario confirmation --output results/pending.json
..\..\..\.venv\Scripts\python.exe demo.py --scenario confirmation --approve --output results/approved.json
..\..\..\.venv\Scripts\python.exe demo.py --replay results/approved.json
..\..\..\.venv\Scripts\python.exe -m pytest -q tests
```

默认completed/2步；loop终止重复；limit只允许一次decide；cancel在开始前取消；confirmation默认等待，--approve仅批准当前内存演示。回放不运行任何工具。

## 代码导航

- [state.py](./state.py)：Status、Action、ToolResult、AgentState和允许转移。
- [tools.py](./tools.py)：工具注册、政策读取和内存工单闭包。
- [policy.py](./policy.py)：正常、重复和需确认的确定策略。
- [agent.py](./agent.py)：决策循环、预算、重复检测、取消、确认与记录。
- [recording.py](./recording.py)：UTF-8录制和只读轨迹播放。
- [demo.py](./demo.py)：命令行场景入口。
- [test_agent.py](./tests/test_agent.py)：正常与关键控制边界。
- [test_recording.py](./tests/test_recording.py)：回放不写入、损坏顺序拒绝。
- [requirements.txt](./requirements.txt)：只用标准库，开发工具复用共享环境。

## 边界

Python3.11+（StrEnum），验证环境3.13。消息是内部教学结构，不是供应商tool API格式。取消不抢占同步阻塞工具；重复检测只看相同名称/参数；批准只绑定当前进程的动作键；无持久幂等或真实授权。completed只表示接受final，并非答案质量或业务成功。录制无签名/脱敏生产方案。

返回[[01_学习指南/14_Agent运行原理与状态机/00 Agent 运行原理与状态机学习地图|教材地图]]。
