---
title: 第 5 讲：用固定评估集比较三个 Prompt
tags:
  - prompt-evaluation
  - benchmark
  - cost
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 5 讲：用固定评估集比较三个 Prompt

> [!nav] 页面导航
> [[01_学习指南/11_LLM_API与Prompt/00 LLM API 与 Prompt 学习地图#学习顺序|单元 11：LLM API 与 Prompt]] · [[01_学习指南/11_LLM_API与Prompt/逐讲学习/04 为超时限流与缓存设置边界|上一讲]] · [[01_学习指南/11_LLM_API与Prompt/逐讲学习/06 完成 API 应用验收|下一讲]]

## 为什么只看一个好答案不够

Prompt A 可能刚好回答了一个简单例子，但在边界输入上失败。评估集（evaluation set）是一组固定的输入和参考答案，用来在相同条件下比较版本。固定测试集就像尺子：如果 Prompt 和测试样本一起换，就看不出变化来自哪里。

对于同一个任务，准备 v1 baseline、v2 加约束、v3 增加 few-shot；每个版本跑相同的样本，固定模型版本、参数、Schema 和失败重试规则。记录原始输出，不能只保存平均分，错误例子更能指导修改。

## 四类指标

- **格式成功率：** 返回文本能解析且满足结构规则的样本数 ÷ 总样本数。
- **任务成功率：** 输出通过必要校验且符合参考标签的样本数 ÷ 总样本数。也可以按分类任务定义精确率、召回率等指标。
- **延迟：** 每个请求的等待时间，至少记录平均值；业务敏感时还看 P50/P95（中位数/95 百分位），避免平均值藏住慢尾部。
- **token 与成本：** 记录 usage 的输入/输出 token；估算成本时用评估当日确认的输入和输出单价。缓存命中、重试与失败请求是否收费要按服务商计费规则处理。

token 数不能直接当成本金额；不同模型和输入/输出方向可能有不同价格，价格也可能更新。不要把教学夹具里的单价当厂商报价。

## 运行评估夹具

工程 `evaluation.demo_records()` 提供同一组三个案例的三版固定输出夹具，其中包含格式失败、类别错判和正确结果。它验证汇总程序是否能算出指标，不调用真实模型，也不证明哪一版 Prompt 在现实模型上更好。

在工程目录运行：

```powershell
..\..\..\.venv\Scripts\python.exe -c "from evaluation import compare_prompt_versions, demo_records; print(compare_prompt_versions(demo_records(), input_price_per_million=1.0, output_price_per_million=4.0))"
```

参数价格单位是“每百万输入/输出 token 的示例价格”。预期报告含 `format_success_rate`、`task_success_rate`、`average_latency_ms`、输入/输出 token 数和 `estimated_cost`；v3 夹具任务正确率为 1.0，v1 格式成功率低于 1.0。这只是预置样本的测试结果。

`compare_prompt_versions` 按 `prompt_version` 分组；每条记录包含 case ID、参考类别、原始输出文本、usage token 和延迟。非法 JSON 或 Schema 错误会进入格式失败分子；只有结构验证成功后才检查任务类别。实际项目还应做语义验证、拒答/安全结果统计，并检查版本之间 case ID 完全相同。

## 如何做真实评估

1. 建立一组覆盖正常、边界、歧义和无法判断输入的样本，写清参考答案与判分规则。
2. 固定服务商、model snapshot/版本、参数、模板、Schema 和 timeout/retry；只改 Prompt。
3. 为每条请求记录版本、样本 ID、状态、输出、usage、延迟、cache hit 和可安全保存的 request ID。PII 按数据策略脱敏；不要记录密钥。
4. 统计格式/任务成功率、延迟分布、实际 token 和按已确认报价计算的金额。
5. 对错误案例分类：指令歧义、资料不足、Schema/解析、事实错误、超时/限流等。明确新版本修复了哪类失败，以及引入了什么回归。

若模型采样有随机性，重复运行或设定可复现参数仍不保证完全相同；报告里写清运行日期与次数。保留评估集，不用它反复改到过拟合；更大的独立测试集之后再验收。

## 练习

**跟做：** 运行夹具，手算 v1 三个案例的格式成功率和任务成功率，再和输出对照。

**独立：** 给同一数据集添加第四个案例，所有三个 Prompt 版本都必须有一条结果。判断如果 v2 漏了该 case，是否能公平比较。

**迁移：** 为真实模型设计实验表头，至少包含 prompt_version、case_id、model_snapshot、status、schema_valid、task_correct、input_tokens、output_tokens、latency_ms、estimated_cost。

> [!example]- 参考答案与解析
> v1 里第一、第三条是有效结构，第二条只是普通文本，所以格式率 2/3；第一、第三条类别与参考相同，任务率为 2/3。v2 中 3 条 JSON 结构都合法，但第三条分类错误，格式率 1、任务率 2/3。v3 夹具 3 条均合法且类别正确，所以两项都是 1。
>
> 漏掉样本会让版本难度不同，不能直接公平比较。应补齐同一 case，或明确从所有版本共同交集重新计算，并报告丢弃了哪些样本。
>
> 实验表中保留 API 状态和原始输出能定位失败。实际成本需要官方 usage 和正确价格，夹具里的数字只供演示公式。

> [!nav] 路线续读
> 若本讲已到当前路线列出的范围末尾，返回原阶段继续下一项或检查产物；继续单元学习时沿下方“下一讲”。
>
> - [[00_学习路线/03 学习模型训练与大模型算法#分支 A：偏好优化|学习模型训练与大模型算法 · 分支 A：偏好优化]]

## 继续学习

> [!next] 下一步
> [[01_学习指南/11_LLM_API与Prompt/逐讲学习/06 完成 API 应用验收|下一讲：完成 API 应用验收]]

> [!info]- 练习与记录
> [[01_学习指南/11_LLM_API与Prompt/示例工程/README#代码导航|查看源码]] · [[01_学习指南/11_LLM_API与Prompt/示例工程/README#运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 11：LLM API、Prompt 与结构化输出|本单元完成清单]]
