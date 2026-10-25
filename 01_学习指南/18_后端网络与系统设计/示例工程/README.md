---
title: 单元 18 示例工程导航
tags: [code, http, jobs]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# 单元 18 示例工程

> [!nav] 页面导航
> [[01_学习指南/18_后端网络与系统设计/00 后端网络与系统设计学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/18_后端网络与系统设计/逐讲学习/01 让两个程序通过 HTTP 交谈|从第一讲开始：让两个程序通过 HTTP 交谈]]

Python标准库本机HTTP原型：合成政策查询、演示用户、SQLite任务、轮询/取消、用户缓存TTL与容量、持久幂等、单实例重启恢复。没有真实模型/外部请求。

## 运行

在本目录VS Code PowerShell终端，使用根共享解释器：

```powershell
..\..\..\.venv\Scripts\python.exe demo.py
..\..\..\.venv\Scripts\python.exe -m pytest -q tests
..\..\..\.venv\Scripts\python.exe -m ruff check .
..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

demo端口自动分配、数据库自有临时目录，结束自动关闭并清理；health200，Alice缓存False/True，BobFalse，无令牌401，模拟上游504，提交202、重复200同ID、最终completed、Bob读任务404。随机ID/端口与线程状态出现时机可不同。

手动终端A `..\..\..\.venv\Scripts\python.exe server.py --port 8765`，终端B同解释器运行client.py；Ctrl+C退出服务。默认持久文件jobs.sqlite在本目录，不自动清空；避免两个实例共用它。作者沙箱的本机socket限制与实测方式见验证记录。

## 代码导航

- [client.py](./client.py)：JSON请求、回环禁代理、HTTPError正文读取。
- [server.py](./server.py)：回环绑定、路由、身份/输入、响应/请求ID、断开日志。
- [service.py](./service.py)：业务查询、32项TTL缓存、工作线程、状态结果公开投影。
- [storage.py](./storage.py)：短连接/事务、按owner查询、并发幂等、认领、取消/恢复。
- [demo.py](./demo.py)：自动服务生命周期与接口演示。
- [test_http.py](./tests/test_http.py)：接口错误、跨用户、幂等、真实回环连接断开。
- [test_service.py](./tests/test_service.py)：TTL可控时钟、事务并发、取消/恢复/容量。
- [requirements.txt](./requirements.txt)：运行仅标准库；pytest/Ruff已在共享环境。

## 边界

http.server不用于公开生产部署，ThreadingHTTPServer请求线程未有界；固定公开令牌非真实认证。无TLS/真实上游超时/模型、分页列表、Redis、SSE/WebSocket、分布式队列/严格一次副作用、队列配额或历史清理。取消状态不抢占同步计算，health不是完整ready检查。恢复running策略只适用同DB单活动实例。JSON接口只覆盖自定义GET/POST路由，其他协议错误可由标准库默认处理。

[[01_学习指南/18_后端网络与系统设计/00 后端网络与系统设计学习地图|单元 18：后端网络与系统设计]]。
