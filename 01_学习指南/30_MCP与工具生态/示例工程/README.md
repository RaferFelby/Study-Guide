---
title: MCP示例工程代码导航
tags: [learning, mcp, protocol]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# MCP示例工程代码导航

> [!nav] 页面导航
> [[01_学习指南/30_MCP与工具生态/00 MCP与工具生态学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/30_MCP与工具生态/逐讲学习/01 认识MCP并区分工具资源与提示|从第一讲开始：认识MCP并区分工具资源与提示]]

## 先运行

在 VS Code 打开本目录，解释器选择工作区根共享 `.venv/Scripts/python.exe`。运行：

```powershell
& ..\..\..\.venv\Scripts\python.exe demo.py --output report-my-01.json
```

报告已存在拒绝覆盖，换新名字。客户端启动本工程 server.py 子进程，UTF-8 JSON一行一消息，没有外网/模型/真实个人信息/写业务。reader/guest是可信启动配置演示，不是真实认证；stdio子进程不自动被操作系统沙箱隔离。

## 代码导航

- [catalog.py](./catalog.py)：固定URI映射、受限资料读取、工具及资源清单。
- [protocol.py](./protocol.py)：2026-07-28请求元数据、discover/list/call/read/get、错误与允许范围。
- [server.py](./server.py)：有界stdin读取、stdout协议、stderr诊断、EOF退出。
- [client.py](./client.py)：本机可信进程启动、串行请求与ID关联、超时、管道和子进程回收。
- [demo.py](./demo.py)：发现、查询、模板、参数/权限/故障与回收报告。
- [refund.json](./fixtures/refund.json) / [support.json](./fixtures/support.json)：两份明确合成资料，不应当作真实政策或客户备注。
- [test_mcp.py](./tests/test_mcp.py)：消息、版本、参数、权限、固定URI、真实stdio、错误同行恢复、坏服务/超时/退出及完整演示。
- [conftest.py](./tests/conftest.py)：只为本工程测试加入源码目录。
- [requirements.txt](./requirements.txt)：运行标准库，测试与格式工具沿用共享环境。

## 结果与检查

reader工具2、guest工具1；非法参数-32602；隐藏工具直接调用isError=True；内部资源应用码1001；合成资料不可用工具isError=True；参数错误后ping仍可用；自有进程全部退出。未调用模型、未接外部应用。

```powershell
& ..\..\..\.venv\Scripts\python.exe -m pytest tests -q
& ..\..\..\.venv\Scripts\python.exe -m ruff check .
& ..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

作者40项测试通过，包含受控临时假服务的坏stdout、错误ID、同时result/error、退出、超时和超长响应。标准库有限子集不提供完整JSON Schema2020-12验证、旧版握手回退、任意通知/并发请求、分页/缓存、HTTP/OAuth或完整符合性验证；不宣称与所有宿主兼容。

## 规范与学习入口

[2026-07-28版本规则](https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning) · [stdio传输](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio)。与旧教程不同，新版每请求携带元数据，不执行initialize。仅启动自己读过的可信程序；server_path是作者测试用途，不从模型/资料中接收程序路径。

[[01_学习指南/30_MCP与工具生态/00 MCP与工具生态学习地图|六讲正文]] · [[90_参考与维护/单元验证/30 MCP与工具生态验证记录|作者实际验证与限制]]。
