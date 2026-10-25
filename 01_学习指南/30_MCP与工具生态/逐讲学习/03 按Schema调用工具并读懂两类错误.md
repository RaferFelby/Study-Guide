---
title: 第 3 讲：按Schema调用工具并读懂两类错误
tags: [learning, mcp, protocol]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 3 讲：按Schema调用工具并读懂两类错误

> [!nav] 页面导航
> [[01_学习指南/30_MCP与工具生态/00 MCP与工具生态学习地图#学习顺序|单元 30：MCP与工具生态]] · [[01_学习指南/30_MCP与工具生态/逐讲学习/02 用stdio连接本地服务并发现能力|上一讲]] · [[01_学习指南/30_MCP与工具生态/逐讲学习/04 读取固定资源并获取提示模板|下一讲]]

## 本讲要解决的问题与前置

工具列出来之后，怎样知道参数该如何填写？请求失败和工具业务失败是不是同一件事？本讲先读 Schema，再正确调用，最后故意制造两类失败。

前置是第 2 讲的客户端、字典键访问、异常处理与 [[01_学习指南/15_工具调用协议与工具设计/00 工具调用协议与工具设计学习地图|输入契约]]。当前只读 get_policy，不增加写操作或模型选择。

## Schema：输入的结构约定

Schema 可理解为“输入应该长什么样的规则”。get_policy 的 inputSchema 说明：输入为对象；topic 是字符串；允许值只有 refund；topic 必填；不接受额外字段。工具名写在 tools/call 的 name 中，业务参数写在 arguments 中。

本例用手写条件验证自己固定工具的少数规则，没有实现任意 JSON Schema 验证器。不能把这些 if 分支拿去声称支持所有 2020-12 Schema、$ref 或组合规则。复杂服务应使用经过批准、版本匹配的成熟实现。

工具描述帮助选择，Schema 帮助校验结构，但真实内容与权限仍要服务端检查。`readOnlyHint=True` 只是声明，不是安全开关，不能跳过执行路径审查。[官方工具接口](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)。

## 最小示例：成功和参数拒绝

在工程新建 `lesson_03.py`：

```python
from client import RemoteError, StdioClient

with StdioClient() as client:
    tool = client.request("tools/list")["tools"][0]
    print("必填字段：", tool["inputSchema"]["required"])
    result = client.request("tools/call", {
        "name": "get_policy", "arguments": {"topic": "refund"}
    })
    print(result["isError"], result["structuredContent"]["version"])
    print(result["structuredContent"]["text"])
    try:
        client.request("tools/call", {
            "name": "get_policy", "arguments": {"topic": "invoice"}
        })
    except RemoteError as error:
        print("参数错误码：", error.code)
    print("连接仍可用：", client.request("ping")["resultType"])
```

运行 `& ..\..\..\.venv\Scripts\python.exe lesson_03.py`。预期 required 为 `['topic']`，成功结果为 False/v1，并含“模拟公开退款期限为30天，仅供教学。”；非法 topic 返回 -32602，随后 ping 为 complete。不要把这份模拟政策当作真实退款规定。

## 按执行顺序理解

第一步读取清单，确认参数规则。第二步发送 name 与 arguments；服务先核对固定工具名称，再核对 arguments 的键与值，最后读取固定夹具。请求的 id 由客户端逐次增加，避免把上一请求的响应错配给下一次。

成功结果有 content 文本块和 structuredContent 字典；本例文本是同一记录的 JSON 表示，字典方便程序读取。isError=False 表示这次工具没有业务错误，不保证记录反映真实世界。

第二次故意传 invoice。它不在当前 enum 中，因此服务返回 JSON-RPC error，客户端抛 RemoteError。except 只处理我们已知的远端协议错误，不把所有异常都吞掉。ping 证明可处理的参数错误没有自动毁掉连接。

## 两类错误必须分开

| 层次 | 本例 | 客户端观察 | 下一步 |
| --- | --- | --- | --- |
| JSON-RPC 请求错误 | 未知方法、参数缺失、版本不支持 | RemoteError，带 code/message | 修正请求或版本选择 |
| 工具执行错误 | 已合法请求，但合成资料不可用或访问拒绝 | result 内 isError=True | 停止使用失败结果，说明原因 |
| 本地连接错误 | 超时、EOF、坏响应或 ID 不匹配 | TimeoutError / ConnectionError | 关闭失效连接，核查后再开 |

工具执行错误不是一份可当政策使用的正常文本。收到 content 时先检查 isError，再读 structuredContent。权限与故障有不同原因，不因为都显示 True 就自动重试。

在本工程终端运行完整 demo 可看到 unavailable 模式的工具错误。也可在自己的脚本使用 `StdioClient(mode="unavailable")`；发送合法 refund 参数后，isError=True 且没有成功资料字典。这个开关是合成故障，不是实际上游网络断开。

## 本节关键错误码

- -32700：收到无法解析的 JSON。
- -32600：不是合法请求形状，例如错误 ID。
- -32601：本服务不支持的方法。
- -32602：参数或要求的元数据不合法。
- -32022：该新版规范定义的协议版本不支持，附支持版本。

前四项属于标准协议错误，新版专有错误按规范使用。本工程资源权限的 1001、资料不可用的 1002 是**自行选择的应用错误码**，不叫“所有 MCP 服务统一权限码”。[基础协议说明](https://modelcontextprotocol.io/specification/2026-07-28/basic/index)。

## 动手与排查

依次试缺 topic、topic=True、加 path 字段，预期都拒绝。不要为“让测试通过”把 additionalProperties 删掉；那会放宽接口而非修复输入。看见 RemoteError 时记录方法/代码/安全参数摘要，不打印真实凭据。

若成功结果里找不到 structuredContent，先检查 isError；不要用空字典代替失败再生成假答案。本例不接受未知工具，也不会把 name 当 Python 代码执行。

## 练习与答案

### 跟做：成功、拒绝、恢复

提示：观察三次请求。完成标准是记录正常 v1、错误 -32602、后续 ping complete，并解释为何连接还活着。

> [!example]- 参考答案与解析
> 参数错误被服务明确响应，协议仍同步，下一合法请求可以处理。它不同于客户端已经读不到或解析不了响应的连接失败。

### 独立：故障结果不能当政策

把 mode 改 unavailable，合法调用 refund，说明应检查哪两个字段。完成标准是不访问不存在的成功记录，不输出假政策。

> [!example]- 参考答案与解析
> 先检查 isError=True，再读取安全的错误文本供显示；没有 structuredContent 资料。应转人工或核查，不把错误提示当知识片段送去回答。

### 迁移：客户要求加入invoice

只改客户端字符串是否够？提示：沿清单、参数检查、夹具、测试、文档追踪。完成标准是列出至少这五项的同步变更。

> [!example]- 参考答案与解析
> 服务需要新增批准资料、更新 inputSchema 与校验逻辑，测试正确和故障路径，再同步文档输出；客户端才使用新能力。协议连接成功不意味着业务功能自然增加。

## 继续学习

> [!next] 下一步
> [[01_学习指南/30_MCP与工具生态/逐讲学习/04 读取固定资源并获取提示模板|下一讲：读取固定资源并获取提示模板]]

> [!info]- 练习与记录
> [[01_学习指南/30_MCP与工具生态/示例工程/README#代码导航|查看源码]] · [[01_学习指南/30_MCP与工具生态/示例工程/README#先运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 30：MCP与工具生态|本单元完成清单]]
