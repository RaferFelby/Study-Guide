---
title: FDE本地政策查询示例工程
tags: [learning, fde, delivery]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# FDE本地政策查询示例工程

> [!nav] 页面导航
> [[01_学习指南/24_FDE需求协作演示与交付/00 FDE需求协作演示与交付学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/24_FDE需求协作演示与交付/逐讲学习/01 用模拟访谈弄清工作流程|从第一讲开始：用模拟访谈弄清工作流程]]

## 先运行什么

VS Code打开本目录，两个PowerShell终端使用共享环境。终端A：

```powershell
& ..\..\..\.venv\Scripts\python.exe mock_source.py --port 8766
```

终端B：

```powershell
& ..\..\..\.venv\Scripts\python.exe server.py --source-url http://127.0.0.1:8766/policies --port 8765
```

浏览器访问http://127.0.0.1:8765/；Ctrl+C分别停止。模拟员工问退款期限得到30天/v1，VIP拒答，访客拒权；源用--mode offline重启模拟故障。--data可选fixtures/policies-v2.json，源启动读取，更新后须重启。仅127.0.0.1，不是生产Web服务器/真实认证。

自动四场景，无需手动两终端：

```powershell
& ..\..\..\.venv\Scripts\python.exe demo.py
& ..\..\..\.venv\Scripts\python.exe -m pytest -q tests
```

运行仅标准库，作者检查使用已有pytest/Ruff。源、身份、政策、访谈与反馈全部模拟；URL引用不可访问，不调用真实LLM，不自动退款。

## 代码导航

- [adapter.py](./adapter.py)：本机HTTP读取、禁重定向/代理、上限与政策契约。
- [service.py](./service.py)：输入/模拟角色前置、规则匹配、受控拒答与异常。
- [mock_source.py](./mock_source.py)：独立合成政策源、正常或503模式。
- [server.py](./server.py)：页面和POST JSON接口，固定假身份映射。
- [page.html](./page.html)：最小普通输出页面，textContent展示不可信文字。
- [demo.py](./demo.py)：实际本机HTTP UAT、自动启动关闭服务。
- [policies-v1.json](./fixtures/policies-v1.json) · [policies-v2.json](./fixtures/policies-v2.json)：版本更新与恢复用合成政策。
- [interview.json](./fixtures/interview.json)：模拟访谈、待证问题与模拟评审要求。
- [test_delivery.py](./tests/test_delivery.py)：正常/失败/接口/身份/版本恢复检查。
- [requirements.txt](./requirements.txt)：运行标准库，无新增环境依赖。

## 边界和阅读

没有真实身份/客户/外部公司API、云部署、生产TLS/资源隔离、分页/限流/持久审计、自动刷新资料。只做受控本机短请求演练。真实服务需要重新选生产框架和安全方案；本例接口适配不能自动授予真实资料使用权。

[[01_学习指南/24_FDE需求协作演示与交付/00 FDE需求协作演示与交付学习地图|学习地图]] · [[90_参考与维护/单元验证/24 FDE需求协作演示与交付验证记录|作者验证]]。
