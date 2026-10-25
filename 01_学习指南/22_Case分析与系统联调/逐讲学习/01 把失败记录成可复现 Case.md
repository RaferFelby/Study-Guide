---
title: 第 1 讲：把失败记录成可复现 Case
tags: [lesson, case, reproducibility]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 1 讲：把失败记录成可复现 Case

> [!nav] 页面导航
> [[01_学习指南/22_Case分析与系统联调/00 Case分析与系统联调学习地图#学习顺序|单元 22：Case分析与系统联调]] · [[01_学习指南/22_Case分析与系统联调/逐讲学习/02 沿轨迹找第一处错误与传播链|下一讲]]

## 本讲任务与前置

“Agent不好用”无法直接修。Case是一个具体任务/失败实例，包括输入、条件、预期、实际与复现证据。复习单元19gold与样本ID，本讲先把五种失败变成别人也能复现的记录。

## 症状与根因的区别

症状是看见的结果，如“拒答了本应回答的问题”；根因是造成结果的机制，如检索只匹配退款期限而不认退钱窗口。模型回答不好可能来自上游没给证据，不能一见症状就修改Prompt。

最小复现是用尽量少的输入和配置仍保留失败。它帮助排除无关因素，但不能删掉权限/用户条件后变成另一任务。真实Case需标数据版本、模型/配置、运行环境和外部状态；合成夹具先让机制可确定。

## 最小示例：读第一条Case

在示例工程新建`lesson_case.py`：

```python
from cases import make_cases
from contracts import Settings
from pipeline import run_pipeline

case = make_cases()[0]
actual = run_pipeline(case["input"], Settings())
print(case["case_id"])
print("预期", case["gold"])
print("实际", actual["output"])
print("是否符合", actual["output"] == case["gold"])
```

运行共享解释器。预期retrieval-alias；gold answered/30；实际refused/None；False。系统只收到case.input，gold留给评估器；不能把根因annotation当模型输入让它照答案修。

## 五条失败台账

| Case | 首次表现 | 待验证根因 | 严重度 |
| --- | --- | --- | --- |
| retrieval-alias | 拒答同义问题 | 检索词形缺同义映射 | medium |
| tool-arguments | failed | account参数与owner契约不同 | medium |
| parse-fence | failed | JSON解析不接受约定围栏格式 | medium |
| permission-cross-user | 返回Bob50天 | 读取前没核当前owner | critical |
| upstream-transient | failed | 暂时只读失败后没有限重试 | high |

严重度是本教学项目的影响分类：跨用户泄漏优先级最高，系统故障高，普通查询可用性中；不是行业唯一等级标准。真实需要数据敏感度、影响用户数、业务风险与恢复成本共同判断。

三条正常回归为Alice普通查询、Bob自身查询、未知VIP明确拒答。只留下失败题会让修复只对失败有利而不知道旧能力坏了没有。

## 动手：生成基线报告

在示例工程终端：

```powershell
..\..\..\.venv\Scripts\python.exe experiments.py --output report-01.json
```

baseline3/8，工具尝试6；所有单项4/8，combined8/8。报告较大时先只看baseline.rows。文件若存在改report-02，旧报告是对照证据，不应覆盖。

case_sha256描述这份代码构造数据的规范化内容版本；trace_id每次新建，实际耗时略有变化正常。来源为author_synthetic、独立人工审核False，不能将此台账写成真实客户事故。

## Case记录模板

在Obsidian笔记写：ID/来源/时间/环境；用户目标与权限范围；输入/依赖状态；预期和依据；实际/错误码/trace；复现步骤；严重度/责任候选；根因假设；单变量验证；修复回归；剩余风险。

起步五条已经足以练流程。后续真实或压力例可持续积累，50条是深化目标，不必为数字复制同题或等收满才修高风险缺口。

## 常见错误

- 只写截图没输入版本：别人无法复现，补条件与命令。
- 复制真实秘密进台账：去标识化，保留最小必要数据和权限。
- 把作者root_cause当自己发现：先沿事件/单变量验证，记录证据。
- 基线全错才值得测：正常回归是防修复引入退步，必须保留。

## 练习与答案

跟做：为retrieval-alias填模板的目标、预期、实际、命令。完成判断：同学只看记录可复现False。

独立：权限Case没有抛异常，为什么仍是失败？

迁移：把你以前运行遇到的一条真实报错整理成Case，标个人运行来源，不把作者输出当自己发生的事。

> [!example]- 参考答案与解析
> 权限Case返回answered并非正确：actor=alice却target=bob，gold应refused。技术流程全成功仍可违反用户/权限契约，需检查真实读取与结果，不靠异常判质量。
>
> 真实记录必须保留实际命令/环境/输入与错误，暂不确定根因时写假设，不凭印象补“测试已通过”。

## 本讲完成后

有可复现Case后，下一讲沿轨迹找第一处偏离。

## 继续学习

> [!next] 下一步
> [[01_学习指南/22_Case分析与系统联调/逐讲学习/02 沿轨迹找第一处错误与传播链|下一讲：沿轨迹找第一处错误与传播链]]

> [!info]- 练习与记录
> [[01_学习指南/22_Case分析与系统联调/示例工程/README#代码导航|查看源码]] · [[01_学习指南/22_Case分析与系统联调/示例工程/README#运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 22：Case分析与系统联调|本单元完成清单]]
