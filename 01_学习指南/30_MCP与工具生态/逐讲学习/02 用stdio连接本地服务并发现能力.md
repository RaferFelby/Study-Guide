---
title: 第 2 讲：用stdio连接本地服务并发现能力
tags: [learning, mcp, protocol]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 2 讲：用stdio连接本地服务并发现能力

> [!nav] 页面导航
> [[01_学习指南/30_MCP与工具生态/00 MCP与工具生态学习地图#学习顺序|单元 30：MCP与工具生态]] · [[01_学习指南/30_MCP与工具生态/逐讲学习/01 认识MCP并区分工具资源与提示|上一讲]] · [[01_学习指南/30_MCP与工具生态/逐讲学习/03 按Schema调用工具并读懂两类错误|下一讲]]

## 本讲要解决的问题与前置

上一讲只构造了消息。现在让客户端真正启动另一个 Python 进程，发现它支持哪些能力。前置是第 1 讲的消息字段、Python 的 with 与异常；如果 with 还陌生，先看下方解释再运行。

本讲顺序：标准流是什么 → 运行完整示例 → 对照发现结果 → 观察关闭进程。阅读源码只关注 client.py 的 __enter__/request/close 和 protocol.py 的 server/discover 分支。

## stdio：通过进程的输入输出通信

stdio 是 standard input/output 的缩写，指标准输入输出。一个进程有 stdin（输入）、stdout（正常输出）、stderr（诊断输出）。本例客户端启动子进程：向子进程 stdin 写请求，从 stdout 读响应，stderr 日志显示到终端。

“子进程”是由当前程序启动的另一个程序实例。它有自己的变量，不会直接共享 lesson_02.py 的字典。实际交换的是 UTF-8 编码后的 JSON 字节，一条消息一行；不是调用同一个 Python 函数那么简单。[官方 stdio 绑定](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio)。

如果把 print("启动成功") 写到服务 stdout，客户端就会尝试把这句话解析成 JSON，产生错误。所以服务日志用 print(..., file=sys.stderr)。客户端打印给你看不受这个限制，它的 stdout 并不是服务的协议管道。

## 最小示例与操作

在同一个工程新建 `lesson_02.py`：

```python
from client import StdioClient

with StdioClient() as client:
    discovered = client.request("server/discover")
    print("版本：", discovered["supportedVersions"])
    print("能力：", sorted(discovered["capabilities"]))
    tools = client.request("tools/list")
    print("工具：", [tool["name"] for tool in tools["tools"]])
    process = client.process
print("服务正常退出：", process.poll() == 0)
```

在工程终端运行：

```powershell
& ..\..\..\.venv\Scripts\python.exe lesson_02.py
```

预期版本 `['2026-07-28']`，能力 `['prompts', 'resources', 'tools']`，工具 `['get_policy', 'get_support_note']`，最后 True。终端还可能先显示“合成MCP服务已启动”的诊断日志；日志与协议使用不同流，不说明有错误。

无需先手动启动 server.py，也无需打开第二个终端输入 JSON。StdioClient 已经启动、连接并管理自己的服务。如果直接运行 server.py，它会等待 stdin，不能把这当成已完成客户端测试。

## 逐步解释生命周期

`with StdioClient() as client:` 进入上下文时调用 __enter__，启动服务并准备读取线程。这个 with 不仅缩进代码，也约定离开时调用 __exit__ 做资源回收。request 构造消息、写入并 flush（立即推送缓冲内容），再等对应响应。

`server/discover` 返回版本与能力；客户端可以了解服务提供什么，但新版并不要求先 discover 才允许其他请求。[官方发现接口](https://modelcontextprotocol.io/specification/2026-07-28/server/discover)。本教材先发现，是为了让你观察能力，再决定调用。

能力字典的 tools={} 表示提供工具功能，不表示已经列出了工具名称；tools/list 才给具体工具清单。`sorted` 排序键用于稳定显示；方括号中的列表推导式取每个工具的 name。若你还不熟推导式，可用普通 for 循环逐个打印 name，其执行含义相同。

离开 with 时先关闭自己的服务输入流，服务读到 EOF（end of file，输入结束）后退出。客户端等待进程结束；超时才终止自己启动的进程。`process.poll()` 返回 None 表示还在运行，0 表示正常退出，所以最后应为 True。

连接持有期间不等于建立了对话身份。每一次请求仍带 _meta，服务不靠“以前说过是哪个客户端”来推断下一请求的能力；本示例也不保存聊天历史。一个进程可以处理多次请求，不需要每个工具调用都重启。

## 能力发现不等于信任

服务自报的名字、版本、description 和 annotations 是提供给宿主参考的元数据。它们可以来自不可信服务，不证明程序真的只读或没有危险行为。本例只启动已阅读的本工程 server.py；不会从工具描述中的命令自动启动陌生程序。

列表响应 ttlMs=0 表示立刻视为不新鲜，cacheScope=private 表示缓存不能跨授权范围共享；它不是“所有缓存都会被删除”的指令。本工程客户端没有保存或复用响应缓存，也没有实现通用分页。清单只有一页，没有 nextCursor。[官方缓存语义](https://modelcontextprotocol.io/specification/2026-07-28/server/utilities/caching)。

## 常见错误与修复

找不到解释器：从正确工程目录运行共享命令，检查根 .venv。服务路径错误：StdioClient 默认按 client.py 所在目录定位 server.py，不依赖一个写死的个人绝对路径。日志被当 JSON：检查服务是否误写 stdout。超时：检查自己启动的服务是否等待了非协议输入；不要无限提高上限。

本地 stdio 没有监听端口，所以“换 8765 端口”不是本节解决方法。Streamable HTTP 是另一种传输，需要单独处理 HTTP、授权与连接，当前不做远程部署。

## 练习与答案

### 跟做：观察发现、清单与退出

完成标准是保存四项输出并解释 capabilities 与工具列表的区别。提示：一个讲支持哪类功能，一个讲具体有哪些工具。

> [!example]- 参考答案与解析
> discover 宣告 tools/resources/prompts，tools/list 返回两个具体名字；退出码 0 表明自有子进程已正常回收。没有调用工具，只执行发现与清单读取。

### 独立：直接请求工具清单

在自己的脚本中删去 discover 请求，保持 tools/list 和 with。预期是什么？先写答案再运行。完成标准是工具清单仍可返回，并解释每次请求携带版本。

> [!example]- 参考答案与解析
> 新版无需初始化会话，tools/list 自己有 _meta，所以可独立处理。删去 discover 不等于删去元数据；旧版兼容客户端的流程另有要求，本工程不支持旧握手。

### 迁移：资料很多时怎么办

如果清单有多页，客户端只读第一页会遗漏什么？完成标准是说明游标和结束条件，以及当前尚未实现。

> [!example]- 参考答案与解析
> 应按 nextCursor 继续请求直到没有下一页，并对页数/时间设上限，防止重复游标循环。本例一页足够教学；不能声称现有客户端可遍历任何真实服务。

## 继续学习

> [!next] 下一步
> [[01_学习指南/30_MCP与工具生态/逐讲学习/03 按Schema调用工具并读懂两类错误|下一讲：按Schema调用工具并读懂两类错误]]

> [!info]- 练习与记录
> [[01_学习指南/30_MCP与工具生态/示例工程/README#代码导航|查看源码]] · [[01_学习指南/30_MCP与工具生态/示例工程/README#先运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 30：MCP与工具生态|本单元完成清单]]
