---
title: 岗位证据与模拟复盘示例工程
tags: [learning, career, evidence]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# 岗位证据与模拟复盘示例工程

> [!nav] 页面导航
> [[01_学习指南/25_岗位分析项目表达与投递复盘/00 岗位分析项目表达与投递复盘学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/25_岗位分析项目表达与投递复盘/逐讲学习/01 从官方岗位页拆出资格与任务|从第一讲开始：从官方岗位页拆出资格与任务]]

## 运行

VS Code打开本目录，共享解释器：

```powershell
& ..\..\..\.venv\Scripts\python.exe demo.py
& ..\..\..\.venv\Scripts\python.exe -m pytest -q tests
```

标准库运行，无新增依赖。预期官方岗位快照5条；结构证据3/8→8/8、文件存在True/语义核验False；五条模拟投递快照coding3/project_explanation2，候选最多两项，pending A04为7天。不会联网刷新、发送简历或判断个人资格。

## 代码导航

- [career.py](./career.py)：快照结构、证据路径/计数、有限文案与模拟阶段/反馈汇总。
- [demo.py](./demo.py)：读合成/官方概括夹具，显示统计与限制。
- [jobs.json](./fixtures/jobs.json)：2026-10-11人工核对五个官方链接的概括，不是完整JD。
- [evidence.json](./fixtures/evidence.json)：作者单元22固定合成任务证据，个人贡献未验证。
- [applications.json](./fixtures/applications.json)：五条假投递与反馈，完全模拟。
- [test_career.py](./tests/test_career.py)：日期/条数/来源/字段/计数/缺证据/去重/空集与失败。
- [requirements.txt](./requirements.txt)：标准库，pytest/Ruff复用共享环境。

## 范围

岗位是否仍开放由本人再核对。证据路径存在不核验指标真实性、个人职责或能力；计数快照不是历史漏斗/录用概率。当前程序只接受模拟投递origin，真实台账需另按个人真实资料建立，不把它改成假来源运行。

[[01_学习指南/25_岗位分析项目表达与投递复盘/00 岗位分析项目表达与投递复盘学习地图|地图]] · [[90_参考与维护/单元验证/25 岗位分析项目表达与投递复盘验证记录|作者检查]]。
