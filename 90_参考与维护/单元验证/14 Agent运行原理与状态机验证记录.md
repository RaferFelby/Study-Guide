---
title: 单元 14 参考工程验证记录
tags: [validation, agent, author-record]
updated: 2026-10-11
cssclasses: ["guide-page", "guide-reference"]
---

# 单元 14 参考工程验证记录

> [[01_学习指南/14_Agent运行原理与状态机/00 Agent 运行原理与状态机学习地图|学习地图]] · [[01_学习指南/14_Agent运行原理与状态机/示例工程/README|代码导航]]

## 环境和实际检查

2026-10-11，Windows共享 `.venv`，Python3.13.12、pytest8.4.2、ruff0.16.9。运行仅标准库，无新安装。

- `python -m pytest -q tests`：19 passed，0.24s。
- `python -m ruff check .`：通过；`python -m ruff format --check .`：9 files already formatted。
- 默认lookup：completed，2次决策，1条政策工具观察，0工单，答案30 days。
- loop：loop_detected，2步，工具只执行1次。
- limit：step_limit，1步，有查询结果但未生成final。
- cancel：cancelled，0步，没有工具执行。
- confirmation：waiting_confirmation，1步，0工单。
- confirmation加--approve：completed，2步，恰好1个内存工单DEMO-1。
- replay approved.json：只读展示录制观察与最终状态，未调用真实工具。

测试还覆盖决策后取消、拒绝确认、批准后参数变化、非法动作、未知工具、执行异常、非JSON参数、错误返回类型、决策状态副本和损坏trace。

## 限制

规则策略不解析任意task；没有真实LLM/API或外部工单。终态completed不等于业务成功；同步工具不支持执行中抢占；动作重复检测不处理全部无进展循环；批准无签名/身份/过期校验；trace不用于跨进程恢复，也不保证防篡改。

共享解释器启动仍显示既有real location提示，但示例与检查实际返回成功。本页属于作者记录，学习者条目仍未勾选。
