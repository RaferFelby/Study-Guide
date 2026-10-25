---
title: 单元 21 示例工程导航
tags: [code, security, tools]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# 单元 21 示例工程

> [!nav] 页面导航
> [[01_学习指南/21_Agent安全与执行边界/00 Agent安全与执行边界学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/21_Agent安全与执行边界/逐讲学习/01 分清用户指令与不可信资料|从第一讲开始：分清用户指令与不可信资料]]

标准库工具边界：受信身份/角色、文档ID注册表/owner/解析路径/字节预算、完整动作批准、内存幂等、六攻击提议、摘要审计链。只读合成夹具、写只在内存；没有shell/环境凭据/网络或任意代码执行接口。

## 运行

本目录VS Code终端使用根共享环境：

```powershell
..\..\..\.venv\Scripts\python.exe demo.py
..\..\..\.venv\Scripts\python.exe -m pytest -q tests
..\..\..\.venv\Scripts\python.exe -m ruff check .
..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

六提议具体code均符合预期；合法Alice读成功；批准建ticket-1、同键replayed=True、改参数needs_confirmation；内存工单1，审计链True。作者沙箱strict resolve拒绝访问，与普通进程差异见记录，未放宽strict检查。

## 代码导航

- [runtime.py](./runtime.py)：TrustedContext、解析提议/工具注册表、权限/路径/预算/写批准。
- [audit.py](./audit.py)：规范化动作指纹、参数摘要与链校验/深复制快照。
- [redteam.py](./redteam.py)：六种来源/越权提议及预期错误。
- [demo.py](./demo.py)：危险拒绝和合法成功对照。
- [policy.txt](./fixtures/policy.txt) · [alice.json](./fixtures/alice.json) · [bob.json](./fixtures/bob.json)：虚构资料/账户。
- [test_security.py](./tests/test_security.py)：攻击/授权/批准/路径/资源/解析/摘要链局限。
- [requirements.txt](./requirements.txt)：仅标准库，不安装沙箱系统。

## 明确边界

身份/批准由应用示例构造，非真实登录/审批；frozen数据类非系统隔离。每runtime串行会话预算；注册目录受控，未解决检查后攻击者并发换文件的全部竞态。批准无期限/撤销存储，幂等/审计内存；摘要无签名锚点，可重算整链/删尾。攻击夹具是提议层，未测真实LLM注入概率。C29-01执行器不适用，不宣称时间/内存/网络沙箱已实现。

[[01_学习指南/21_Agent安全与执行边界/00 Agent安全与执行边界学习地图|返回地图]]。
