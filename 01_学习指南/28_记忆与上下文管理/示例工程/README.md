---
title: 记忆与上下文示例工程代码导航
tags: [learning, memory, context]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# 记忆与上下文示例工程代码导航

> [!nav] 页面导航
> [[01_学习指南/28_记忆与上下文管理/00 记忆与上下文管理学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/28_记忆与上下文管理/逐讲学习/01 区分临时上下文长期偏好与外部知识|从第一讲开始：区分临时上下文长期偏好与外部知识]]

## 先运行

VS Code打开本目录，选择工作区根共享解释器：

```powershell
& ..\..\..\.venv\Scripts\python.exe demo.py
```

仅标准库；用户、时间、确认及聊天全部合成，不调用LLM、不联网、不读取真实个人资料。每次临时SQLite自动关闭清理，不创建单元.venv。完整步骤见 [[01_学习指南/28_记忆与上下文管理/00 记忆与上下文管理学习地图|学习地图]]。

## 代码导航

- [memory.py](./memory.py)：偏好白名单、模拟确认、UTC时间、来源/置信标签、事务版本、到期检索、按用户删除与资源关闭。
- [context.py](./context.py)：UTF-8字节教学Tokenizer、固定结构/当前问题预算、有损goal摘要、成对历史移除与遗漏报告。
- [demo.py](./demo.py)：故意误记→复核纠正、隔离、预算压缩、过期与删除演练。
- [confirmations.json](./fixtures/confirmations.json)：模拟原始确认与期望值，明确不是现实同意。
- [test_memory.py](./tests/test_memory.py)：命中/失败边界、并发版本、删除/隔离、连接关闭、预算/来源与当前问题保护。
- [requirements.txt](./requirements.txt)：标准库说明，测试工具在已有共享环境。

## 验证命令与预期

```powershell
& ..\..\..\.venv\Scripts\python.exe -m pytest tests -q
& ..\..\..\.venv\Scripts\python.exe -m ruff check .
& ..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

演示created1、unchanged1、updated2，误记Chinese纠正English；24条合成历史带偏好时输入2663→592，输入上限640；删除alice后无命中/事件，bob保留。作者验证见 [[90_参考与维护/单元验证/28 记忆与上下文管理验证记录|验证记录]]，不代表学习者完成。

owner需真实应用提供可信身份，本API自身不认证。TTL仅筛掉过期记录；delete删除当前表与事件，不保证擦除备份/源对话/已生成报告。记忆字段作为数据组织，不构成LLM提示注入防护证明。真实模型需匹配Tokenizer及最终聊天模板；本字节预算不等于任何LLM token计量。
