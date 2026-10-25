---
title: 第 5 讲：按token预算压缩历史而非截断问题
tags: [learning, memory, context]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 5 讲：按token预算压缩历史而非截断问题

> [!nav] 页面导航
> [[01_学习指南/28_记忆与上下文管理/00 记忆与上下文管理学习地图#学习顺序|单元 28：记忆与上下文管理]] · [[01_学习指南/28_记忆与上下文管理/逐讲学习/04 删除用户记忆并核查残留范围|上一讲]] · [[01_学习指南/28_记忆与上下文管理/逐讲学习/06 用命中误记与删除Case验收记忆|下一讲]]

## 本讲要解决的问题与前置

长对话超过模型窗口前，需要决定保留哪些信息。本讲精确计算当前教学Tokenizer下的输入，预留输出，再压缩旧历史；不截断当前问题或系统固定结构。前置是第1讲三种记忆和 [[01_学习指南/10_Tokenizer对话模板与训练样本/00 Tokenizer 对话模板与训练样本学习地图|Tokenizer与模板]]。

快速顺序：先算预算 → 看计数器范围 → 运行编译 → 查看被移除来源 → 看损失 → 练习。读context.py的serialize_prompt、summarize_history、compile_context。

## 预算的最小算术

上下文窗口是一次模型调用能承载的输入加生成位置上限，实际值必须核对目标模型。本例人为设置768教学token，输出预留96、余量32，所以输入最多640。余量用于避免紧贴极限；其大小是教学选择，不是所有模型标准。

ByteTokenizer把UTF-8每个字节视为一个教学token，因此英文hi为2，中文你好为6。它只是明确且可测的计数协议，不是常见LLM的子词Tokenizer，也不是按中文字符数估计。真实接入必须用该模型Tokenizer，把角色、特殊token和聊天模板都计入，再为输出预留空间。

## 最小示例与操作

工程新建 `lesson_05.py`：

```python
import json
from context import ByteTokenizer, compile_context
from demo import make_history

tokenizer = ByteTokenizer()
print("hi与你好：", len(tokenizer.encode("hi")), len(tokenizer.encode("你好")))
result = compile_context([], make_history(), "What should I study next?", "alice")
payload = json.loads(result["prompt"])
print("输入：", result["input_tokens"], "上限：", result["input_capacity"])
print("移除轮次：", len(result["removed_turn_ids"]))
print("当前问题：", payload["current_user"])
print("摘要：", result["summary"])
```

执行 `& ..\..\..\.venv\Scripts\python.exe lesson_05.py`，第一行2/6，输入必须≤640，移除若干偶数条旧turn，当前问题完整保留。这里没传偏好，所以数值不同于demo带记忆的592；先检查条件，不强行把两组数写成一样。

## 逐步讲解：预算先于调用

1. 校验window/output_reserve/margin为正整数且有输入空间；校验当前输入、历史字段、成对角色和用户记忆范围。
2. 用同一serialize_prompt组装固定系统字段、memory_data、summary_data、recent_history、current_user，计数涵盖JSON结构，而不是只数用户文字。
3. 如果最小固定结构加当前问题已超640，明确BudgetExceeded，要求缩短/拒绝；不偷偷砍掉当前问题尾部，尤其那里可能有约束或金额。
4. 否则每次移除最早的一对user/assistant，重新生成旧段摘要并重数，直到能放下。原始history列表不被修改。
5. 所有旧历史都移除仍超预算时，可以弃摘要，再弃部分可选记忆，并返回history_summary_dropped及dropped_memory_keys。它不是无损压缩，删除信息必须可见。

本例输出只是待调用上下文，没有LLM生成，因此预留96不验证真实模型最大生成限制；迁移时还需把同一数值传到后端生成上限。token计数必须和实际最终发送模板一致，不能计一个JSON却发送另一串chat模板。

## 摘要保留什么、丢掉什么

规则摘要只从较早user文本提取以 `goal:` 开头且≤80字符的目标，最多最近三种，带source_id；其他内容只计omitted_turns，不声称已总结。重复目标去重并指向最近来源。这个简单方法用于检查来源与损失，不是通用对话总结器。

demo的24条历史从2663字节token压到592，移除22条，保留最后user/assistant对，摘要保留目标和u-9来源。历史金额、日期、例外条件如果未按规则保留就丢失，执行高影响任务必须检索原文或确认，不能从摘要猜补。

JSON把记忆与摘要放在数据字段，但这不是抵抗模型提示注入的安全保证。本例没调用LLM，所以只能检查数据布局；权限/工具边界还由应用代码执行，不让记忆中的“忽略限制”获得系统权力。

## 动手与常见错误

把window降到300、reserve40、margin20；结果应≤240，可能summary被弃，报告标记要查看。把current改为1000个x应报BudgetExceeded；恢复后运行正常。未出错不表示记忆全部保留，检查丢弃字段。

错误做法：按字符数假装真实token；不预留输出；先发请求等超限再砍；只保留最后任意N字符导致角色/句子被切断；摘要把猜测当事实；丢信息却报告“完整历史已保留”。按步骤先预算、后选择、再核查来源。

## 练习与完成标准

### 跟做：预算恒等式

验证input_tokens+output_reserve+margin≤window。完成标准是明确tokenizer名称和实际序列化口径。

> [!example]- 参考答案与解析
> 默认上限640=768-96-32。demo的592+96+32=720≤768，剩48余量；不是某商业模型窗口大小。

### 独立：窗口1024

输出预留200、余量24，输入多少？

> [!example]- 参考答案与解析
> 800。计入系统、记忆、摘要、角色模板和当前问题全部输入；不能再给每部分各800。

### 迁移：模型总结器

若用LLM生成摘要，还需检查什么？

> [!example]- 参考答案与解析
> 原文来源、事实是否被改写/遗漏、猜测标记、隐私、摘要长度与成本、角色注入边界及版本。保留可回查依据和错误Case，不能因为“模型生成”就默认忠实或安全。

> [!nav] 路线续读
> 若本讲已到当前路线列出的范围末尾，返回原阶段继续下一项或检查产物；继续单元学习时沿下方“下一讲”。
>
> - [[00_学习路线/02 学习Agent与RAG应用#阶段 5：审计、安全与整合|学习Agent与RAG应用 · 阶段 5：审计、安全与整合]]

## 继续学习

> [!next] 下一步
> [[01_学习指南/28_记忆与上下文管理/逐讲学习/06 用命中误记与删除Case验收记忆|下一讲：用命中误记与删除Case验收记忆]]

> [!info]- 练习与记录
> [[01_学习指南/28_记忆与上下文管理/示例工程/README#代码导航|查看源码]] · [[01_学习指南/28_记忆与上下文管理/示例工程/README#先运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 28：记忆与上下文管理|本单元完成清单]]
