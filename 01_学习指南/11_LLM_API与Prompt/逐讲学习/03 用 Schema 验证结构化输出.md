---
title: 第 3 讲：用 Schema 验证结构化输出
tags:
  - json-schema
  - structured-output
  - validation
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 3 讲：用 Schema 验证结构化输出

> [!nav] 页面导航
> 首次主线 10/11 · [[01_学习指南/11_LLM_API与Prompt/00 LLM API 与 Prompt 学习地图#学习顺序|单元 11：LLM API 与 Prompt]] · [[01_学习指南/11_LLM_API与Prompt/逐讲学习/02 写清指令与组织上下文|上一讲]] · [[01_学习指南/11_LLM_API与Prompt/逐讲学习/04 为超时限流与缓存设置边界|下一讲]]

## 为什么不能只要“返回 JSON”

模型回答经常是给人读的文字，但程序要读取字段、数字和类别，需要结构化数据。JSON 是常用文本数据格式。只让模型“请返回 JSON”仍不能保证没有代码围栏、漏字段或字段值类型错误。

JSON Schema 是描述 JSON 数据形状的规则，例如对象有哪些字段、字段类型是什么、某字段只能选哪些值。受约束输出（constrained/structured output）是服务端尽可能让生成结果遵循 Schema 的能力；它减少格式问题，但应用端仍应解析和验证结果。

## 本地示例的两层验证

示例任务是从客服原文抽取分类：

```json
{"category":"refund","priority":2,"evidence":"申请退款"}
```

第一层 `validate_result_schema` 检查 JSON 是否为对象、必需字段有没有、是否出现多余字段、类型/枚举/范围是否符合约定。第二层 `validate_result_semantics` 检查 evidence 确实是原文里的连续片段，并检查分类与主题词是否明显矛盾。

数据通过 JSON parsing 只表示语法可读；通过 Schema 只表示形状合格；仍不代表内容真实或分类正确。比如 `{category:refund,...}` 不是合法 JSON；`{"category":"refund","priority":99,...}` 有 JSON 但不符合字段约束；类别、证据都合规也可能答错任务。

在工程目录运行演示：

```powershell
..\..\..\.venv\Scripts\python.exe demo.py
```

再单独运行结构化输出测试，检查 JSON 语法、缺字段、错误类型、证据不在原文和类别矛盾等情况：

```powershell
..\..\..\.venv\Scripts\python.exe -m pytest -q tests\test_structured_output.py
```

预期所有结构测试通过。若真实 API 文本漏掉双引号、返回 Markdown 代码围栏、priority 写成字符串、或 evidence 不在原文里，程序会抛出带原因的 `OutputValidationError`。

## API 侧的 Schema 约束

服务商可能支持让模型按 JSON Schema 输出。以 OpenAI Responses 风格为例，`text.format` 可声明 `type: "json_schema"`、名称、`strict` 与 schema；官方说明 strict 仅支持 JSON Schema 的一个子集，且不同模型/API 可能限制不同。[Structured Outputs/API reference](https://platform.openai.com/docs/api-reference/responses-streaming/response/refusal)。

格式约束发生在生成服务一侧；本地 `json.loads`、schema 校验和业务校验则是接收边界的防线。拒答、输出不完整、响应失败和版本不支持 schema 都需要按真实响应状态处理，不能假定一收到 200 就必有可用 JSON。原始 Responses 输出也可能有多种 item 类型，先正确提取 assistant text 再解析。[响应输出结构](https://platform.openai.com/docs/api-reference/responses-streaming/response/refusal)。

本工程为零依赖，手写的 validator 只覆盖本课程所需字段，不是完整 JSON Schema 引擎。真实项目要用服务端受约束输出配合可信 JSON Schema 实现，不能把这个小函数当成标准库完整支持 Schema。

## 练习

**跟做：** 在 `tests/test_structured_output.py` 找一个错误结果，改为正确值，再运行 `pytest`。

**独立：** 设计一个“会议提取” Schema，包含 `date`（字符串）、`attendees`（字符串数组）和 `decision`（字符串）；另写一条语义规则检查日期是否存在于会议原文。

**迁移：** API 返回一个形状符合 Schema、但引用来源中不存在的证据。说明为什么格式成功率可能为 100%，真实任务成功率仍不合格。

> [!example]- 参考答案与解析
> 按示例表格用例修复缺失字段/错误 enum/type/range/多余字段，先运行对应测试，再运行全套测试；不可删掉失败断言。
>
> 会议 Schema 要明确 required 字段、数组 items 类型、未知字段是否允许。当前工程的最小 validator 不支持任意嵌套 schema；练习目标是先写出契约，再用适合的库/服务验证。
>
> 格式成功率只检查文本是否可解析且符合结构。证据不真实属于语义/任务质量错误，应降低语义或任务成功率并触发人工审核/降级。

## 排错顺序

1. 看原始文本是否是严格 JSON；先修语法，不用正则截取花括号来掩盖问题。
2. 看报错字段路径/规则，修必填项、额外项、类型、枚举或范围。
3. 结构过关后，再检查证据是否来自输入、字段之间是否矛盾。
4. 若 API 侧 Schema 被拒绝，核对当前 API 版本、模型能力和受支持的 JSON Schema 子集。

## 继续学习

> [!next] 下一步
> [[01_学习指南/11_LLM_API与Prompt/逐讲学习/04 为超时限流与缓存设置边界|首次主线下一步：为超时限流与缓存设置边界]]

> [!info]- 练习与记录
> [[01_学习指南/11_LLM_API与Prompt/示例工程/README#代码导航|查看源码]] · [[01_学习指南/11_LLM_API与Prompt/示例工程/README#运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 11：LLM API、Prompt 与结构化输出|本单元完成清单]]
> [[00_学习路线/01 从零开始建立共同基础|回看首次学习阶段]]
