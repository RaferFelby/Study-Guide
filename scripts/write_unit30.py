"""编写MCP新版有限stdio教学单元；仅作为显式执行的作者工具。"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "01_学习指南/30_MCP与工具生态"
MAP = "00 MCP与工具生态学习地图"
LESSONS = [
    "01 认识MCP并区分工具资源与提示",
    "02 用stdio连接本地服务并发现能力",
    "03 按Schema调用工具并读懂两类错误",
    "04 读取固定资源并获取提示模板",
    "05 验证权限拒绝超时与连接回收",
    "06 比较MCP与直接函数调用并完成验收",
]


def write(name, body, title=None):
    path = ROOT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    heading = title or path.stem
    path.write_text(
        f"---\ntitle: {heading}\ntags: [learning, mcp, protocol]\nupdated: 2026-10-12\n---\n\n# {heading}\n\n"
        + body.strip()
        + "\n",
        encoding="utf-8",
    )


def lesson(number, body):
    previous = (
        f"[[{LESSONS[number - 1]}|上一讲]]"
        if number
        else "[[../../29_规划工作流与重新规划/00 规划工作流与重新规划学习地图|前一单元]]"
    )
    following = (
        f"[[{LESSONS[number + 1]}|下一讲]]" if number < 5 else f"[[../{MAP}|返回地图]]"
    )
    write(
        f"逐讲学习/{LESSONS[number]}.md",
        f"[[../{MAP}|单元地图]] · {previous} · {following}\n\n" + body,
    )


def main():
    lesson(
        0,
        r"""
## 本讲要解决的问题与前置

你已经会给 Agent 写一个 Python 工具函数。如果另一个应用也想使用它，怎样让对方知道函数叫什么、参数如何填写、结果怎样读取？本讲先分清 MCP 的角色和消息，不急着接入陌生应用。

前置是 Python 的函数、列表、字典、字符串与 JSON。若不熟，请先读 [[../../01_Python工程化/00 Python 工程化学习地图|Python 基础]] 和 [[../../15_工具调用协议与工具设计/00 工具调用协议与工具设计学习地图|工具参数与 Schema]]。后续的子进程/上下文管理会在第 2 讲解释；不默认你会写网络服务器。

学习顺序：认识角色 → 分类三种能力 → 看一个请求字典 → 判断谁执行了什么。

## MCP解决什么问题

MCP 是 Model Context Protocol，中文可理解为“模型上下文协议”。协议是双方约定的消息格式与交互规则。它帮助应用以统一方式发现和使用工具、资料及提示模板；不负责给语言模型安装知识，也不保证模型的答案正确。

像不同设备使用统一插口，但插口只约定如何连接：设备是否可信、你能否用、输出是否正确仍要检查。实际机制是客户端发送带方法名和参数的消息，服务端校验后返回对应结果。不能把“接上了 MCP”当作“已经拥有所有权限”。

本单元采用核对过的 **2026-07-28 版本**。每个请求都携带版本与客户端能力；较早的 2025-11-25 及以前版本使用 initialize 握手。不同版本的教程不能直接拼起来。[官方版本说明](https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning)。本工程只实现有限教学子集，不提供旧版自动回退或完整 SDK。

## 三个角色，不是三个模型

| 角色 | 职责 | 本单元对应 |
| --- | --- | --- |
| Host，宿主应用 | 决定接哪些服务、允许什么操作、如何展示结果 | demo.py 及你启动示例的终端 |
| Client，客户端 | 发送协议请求，关联响应，处理连接 | client.py 的 StdioClient |
| Server，服务端 | 公布能力，检查输入及权限，执行具体功能 | server.py 与 protocol.py |

服务端和客户端可以都是普通 Python 程序。这里没有语言模型参与；未来宿主可以把已允许的工具交给模型选择，但执行和权限校验仍由程序负责。客户端自己的显示名称也不是身份认证凭据。

## 工具、资源、提示各自做什么

本例围绕两份**合成资料**：公开退款政策和内部支持备注，没有真实客户信息。

| 能力 | 学习任务 | 本例方法 | 结果是什么 |
| --- | --- | --- | --- |
| Tool，工具 | 按参数执行一项操作 | tools/call | 文本或结构化操作结果 |
| Resource，资源 | 按 URI 读取一份上下文资料 | resources/read | 资料内容 |
| Prompt，提示模板 | 根据参数准备一组消息 | prompts/get | 交给宿主选择使用的消息 |

调用工具可能产生副作用，因此不能只看名字判断是否安全；本例工具都是只读。资源 URI 是资源身份，例如 knowledge://public/refund-v1，不代表程序可以读任意磁盘文件。提示模板是文本准备，取到它不等于调用了模型，更不等于执行了里面提到的工具。

目前必须掌握这三个区别。图片、音频、订阅、模型采样、交互式补充输入属于以后需要时再加入的能力，本工程未实现。

## 最小示例：先看请求，不启动服务

在 VS Code 打开 `01_学习指南/30_MCP与工具生态/示例工程`，新建 `lesson_01.py`，保存：

```python
from protocol import VERSION_KEY, build_request

request = build_request(1, "tools/list")
print(request["jsonrpc"], request["id"], request["method"])
print(request["params"]["_meta"][VERSION_KEY])
print("已经收到结果吗？", "result" in request)
```

打开“终端 → 新建终端”，确认当前目录为这个示例工程。运行：

```powershell
& ..\..\..\.venv\Scripts\python.exe lesson_01.py
```

`&` 让 PowerShell 执行随后指定的程序；`..` 返回上级目录，三个 `..` 回到工作区根。选择同一个共享解释器，不创建单元环境。预期三行：`2.0 1 tools/list`、`2026-07-28`、`已经收到结果吗？ False`。

## 逐行理解执行过程

第一行导入常量和函数，没有启动服务。`VERSION_KEY` 是元数据键的完整名字，用常量避免手写拼错。`build_request` 返回字典；`1` 是请求 ID，供响应对号，`tools/list` 是请求列出工具的方法名。

`request["params"]["_meta"]` 先取参数字典，再取其中的元数据。元数据描述版本与客户端能力，和工具的业务参数不是一回事。最后一行检查字典是否已经包含 result：这里只构造消息，因此为 False。

JSON-RPC 是用 JSON 表示远程调用的约定：请求通常有 jsonrpc/id/method/params，响应有对应 id 和 result 或 error。JSON 字典能构造不意味着对方接受它；第 2 讲才真正送到另一进程。

## 常见错误与排查

`ModuleNotFoundError: protocol`：检查脚本是否在本单元示例工程，不是根目录或其他单元。`KeyError`：核对大小写和键名，不能把字段名的中文解释直接写进代码。只看打印的工具名就说“工具已经执行”：本讲没有发送，也没有服务器结果。

看到旧教程先 initialize 时，先核对协议版本，不把它当所有版本都必须执行的第一步。读源码时从 [[../示例工程/README|代码导航]] 进入，当前关注 build_request 即可，不需一次理解所有分支。

## 练习与答案

### 跟做：指出三行输出的证据

提示：区分版本、请求身份和是否已有响应。完成标准是能解释为什么最后是 False，而不是只复述数字。

> [!example]- 参考答案与解析
> 2.0 是 JSON-RPC 消息版本，1 是请求 ID，2026-07-28 是 MCP 协议版本，两个版本不是同一项。函数只返回请求字典，所以没有 result，尚未发送也未执行工具。

### 独立：给三项需求分类

“查询退款政策”“读取某一版原文”“准备带问题的提问模板”分别适合哪种能力？提示：看要执行操作、取资料还是生成消息。完成标准是说明分类理由及结果类型。

> [!example]- 参考答案与解析
> 参数化查询可用工具，固定原文可用资源，提问模板可用提示。工具也可以返回资料，但三类接口表达不同意图；分类不自动赋予权限。

### 迁移：同一服务接两个应用

列出需要复用的部分和各应用仍要决定的部分。完成标准是包含能力描述、协议客户端、允许范围与展示方式。

> [!example]- 参考答案与解析
> 服务复用业务函数和能力描述；应用各自接客户端、配置可信服务、批准允许范围和显示结果。共享协议不代表共享用户身份、审批或模型 API。
""",
    )
    lesson(
        1,
        r"""
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

列表响应 ttlMs=0、cacheScope=private，表示本例不复用缓存。字段存在不意味着客户端自动获得缓存功能；我们的客户端没有实现通用缓存和分页。清单只有一页，没有 nextCursor。

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
""",
    )
    lesson(
        2,
        r"""
## 本讲要解决的问题与前置

工具列出来之后，怎样知道参数该如何填写？请求失败和工具业务失败是不是同一件事？本讲先读 Schema，再正确调用，最后故意制造两类失败。

前置是第 2 讲的客户端、字典键访问、异常处理与 [[../../15_工具调用协议与工具设计/00 工具调用协议与工具设计学习地图|输入契约]]。当前只读 get_policy，不增加写操作或模型选择。

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
""",
    )
    lesson(
        3,
        r"""
## 本讲要解决的问题与前置

同一份政策既能通过工具查询，也能通过资源读取；提示模板又是什么？本讲实际读取固定 URI 并取一份提示，判断哪些步骤只是准备资料、哪些需要另外调用模型。

前置是第 3 讲错误分层、Python 列表/字典与 json.loads。阅读 catalog.py 固定 URI 映射和 protocol.py 的 resources/read、prompts/get 分支。

## URI不是操作系统路径

URI 是 Uniform Resource Identifier，统一资源标识符，用来给资源一个明确身份。本例 `knowledge://public/refund-v1` 中 knowledge 是自定义方案，public 表示示例分类，refund-v1 表示固定资源。这个字符串不会直接拼进磁盘路径，也不会自动发网络请求。

catalog.py 只把两个明确 URI 映射到本工程 fixtures/refund.json 和 support.json。未知 URI 先拒绝；读取前还检查演示权限。它不是“给模型一个 file:// 就可以随便读盘”的文件服务。[官方资源接口](https://modelcontextprotocol.io/specification/2026-07-28/server/resources)。

资源是否进入模型上下文由宿主决定。资源内容也可能包含不可信指令；读到“忽略规则”不能因此改变权限。当前资料是合成的，但生产应保留来源与版本，并沿单元 21 的信任边界处理。

## 最小示例与操作

新建 `lesson_04.py`：

```python
import json
from catalog import PUBLIC_URI
from client import StdioClient

with StdioClient() as client:
    resources = client.request("resources/list")["resources"]
    print("资源个数：", len(resources))
    result = client.request("resources/read", {"uri": PUBLIC_URI})
    record = json.loads(result["contents"][0]["text"])
    print(record["uri"], record["version"])
    prompt = client.request("prompts/get", {
        "name": "policy_question", "arguments": {"question": "退款期限是多少？"}
    })
    message = prompt["messages"][0]
    print(message["role"], message["content"]["type"])
    print(message["content"]["text"])
```

运行 `& ..\..\..\.venv\Scripts\python.exe lesson_04.py`。reader 配置预期两份资源；记录 URI 为公开退款 URI，版本 v1；提示为 user/text，文本以“问题：退款期限是多少？”结束。

## 一步一步解释结果

resources/list 返回可见清单，里面主要是身份和格式，不是原文。resources/read 返回 contents 列表；本例只有一块，先取 `[0]`，再取 text。因为 MIME 类型是 application/json 且本工程约定 text 内装 JSON，才使用 json.loads 解析。别把所有资源的 text 都当 JSON，真实服务还可能是普通文本或其他内容。

MIME 类型是内容格式标签，帮助应用选择读取方式，不证明内容可信。资源返回 ttlMs=0/private，本客户端没有缓存；不会因为上一轮 reader 读取过，就给 guest 返回旧缓存。

prompts/get 返回 messages，role 为 user，content 为 text。本例拼接已验证的问题文本，长度限制 1～200 字符。提示选择通常由用户或应用界面决定；协议本身不强制某一种界面。[官方提示接口](https://modelcontextprotocol.io/specification/2026-07-28/server/prompts)。

取提示不读取内部资料，不执行工具，也不调用模型。要真正回答问题，宿主还需选择获批的模型接口、准备适当上下文、控制费用，再处理模型输出；这些在当前单元都未执行。因此输出模板文本不能写成“LLM 已回答”。

## 动手：把“身份、资料、提示、答案”分开

在笔记写四栏：公开 URI、读取的合成内容和版本、取到的消息、真实模型最终答案。前三栏填写本次观察，最后一栏填“未调用模型”。再把问题改为另一个短文本，确认只有提示消息变化，资料版本不会随问题文本改变。

如果要试未知 URI，使用自己的脚本并捕获 RemoteError，不修改公共映射。不存在的资源返回 -32602，而不是空 contents。这样使用者能区分“资料不存在”和“合法资料恰好没有文本”。

## 常见错误与修复

`KeyError: contents`：可能误把 prompts/get 结果当资源结果，先看方法和顶层键。JSONDecodeError：确认资源 MIME/内容契约，不盲目 json.loads。任意文件能否读取：本例仅固定映射，未知 URI 拒绝。模板里出现问题就当作回答：它只是输入消息，不包含语言模型计算。

输入 `<script>` 等字符不会在终端执行，但这不证明接到网页或模型后没有注入风险；真实显示层需按自己的格式处理，模型上下文也不能让资料改变工具权限。

## 练习与答案

### 跟做：三类结果对号

提示：看 resources、contents、messages。完成标准是指出清单、原文块和提示消息分别在哪，不混用 `[0]` 的对象。

> [!example]- 参考答案与解析
> resources 是清单条目，contents 是读出的原文块，messages 是供宿主使用的对话消息。本例每块都是 text，但用途和结构不同。

### 独立：修改问题不改资料

把 question 改为“资料不足时怎么办？”，预测哪些输出改变。完成标准是再次读到 v1，而模板结尾改变，仍无模型答案。

> [!example]- 参考答案与解析
> 资源 URI 与映射不变，版本仍 v1；prompts/get 使用新的 question 拼接消息。没有把 question 写进资料文件或执行工具。

### 迁移：大文件与资源更新

真实资源内容很大且会更新，你会增加哪些约定？完成标准是包含大小/分段、版本/来源、缓存范围与失效、权限及未测项。

> [!example]- 参考答案与解析
> 需要有界读取或分页分块，明确格式与版本，按权限和来源区分缓存并处理失效；资源更新订阅需明确实现再声明能力。本工程只有小夹具，未实现订阅或大文件流式读取。
""",
    )
    lesson(
        4,
        r"""
## 本讲要解决的问题与前置

不在工具清单里的内部工具，能否直接猜名字调用？客户端不回收超时服务会怎样？本讲把权限检查与连接回收都变成可观察的失败路径。

前置是前四讲和 [[../../21_Agent安全与执行边界/00 Agent安全与执行边界学习地图|权限与资料边界]]。本例 reader/guest 是**受信启动配置的模拟范围**，不是用户名、密码、真实登录或 OAuth。没有向外部系统申请权限。

## 过滤清单只是第一层

guest 的 tools/list 只显示 get_policy，resources/list 只显示公开政策。但是隐藏工具名称不是安全机制：调用者可能已经知道 get_support_note。因此 tools/call 与 resources/read 在实际读取前都再检查允许范围。

请求 _meta 中的 clientInfo 是自报信息，写成 admin 不会提升权限；capabilities 表示客户端能处理哪类协议功能，也不等于业务授权。本例的 audience 从可信宿主启动参数取得，不允许工具 arguments 覆盖。[发现接口的身份说明](https://modelcontextprotocol.io/specification/2026-07-28/server/discover)。

这只验证应用层分支。能在你的电脑上启动 reader 进程的人也能改配置，所以不能把这套开关当真实访问控制系统。启动第三方服务器本身也是执行程序，MCP 不自动给子进程装操作系统沙箱。

## 最小示例：直接调用仍然拒绝

新建 `lesson_05.py`：

```python
from catalog import INTERNAL_URI
from client import RemoteError, StdioClient

with StdioClient(audience="guest") as client:
    print([tool["name"] for tool in client.request("tools/list")["tools"]])
    denied = client.request("tools/call", {
        "name": "get_support_note", "arguments": {}
    })
    print("工具被拒绝：", denied["isError"])
    try:
        client.request("resources/read", {"uri": INTERNAL_URI})
    except RemoteError as error:
        print("资源拒绝码：", error.code)
    process = client.process
print("自有服务已退出：", process.poll() == 0)
```

运行 `& ..\..\..\.venv\Scripts\python.exe lesson_05.py`。预期列表只有 get_policy，工具 isError=True，资源错误码 1001，最后 True。1001 是本工程约定的应用码，其他服务可不同。

## 逐步追踪拒绝发生的位置

第一步清单过滤没有读内部夹具。第二步故意指定隐藏名称，服务识别它但在 read_record 前检查 audience，于是返回受控错误文本。第三步访问内部 URI，同样在读取前拒绝，但资源 API 使用 JSON-RPC 应用错误。

tests/test_mcp.py 中的权限测试把资料读取函数替换为“一调用就报错”的函数。guest 拒绝测试仍通过，证明拒绝分支没有先读取后遮住显示。这个证据比只检查前端未显示内部文本更具体。

## 超时、EOF和坏响应为什么要关闭连接

客户端只支持一次一个请求，等待默认 3 秒。超时后，旧请求也许稍后返回；继续沿原连接发新请求可能把旧结果错配。所以本例在超时或传输异常时关闭自有子进程，后续明确建立新连接，不静默把迟到消息当新响应。

EOF 指输出流已结束，不是成功的空结果；错误 id、非法 JSON、超长行也是连接失效。本客户端的读取线程有界读取，队列最多 8 项，拒绝无界积累；没有实现任意通知、多请求并发或通用客户端路由。

关闭过程先关 stdin，等待 1 秒；仍不退出才 terminate，再等待，必要时 kill。只处理 client 自己启动的 process，不寻找和结束其他 Python 进程。close 可重复调用，异常退出 with 时也会回收。

工具正常给出参数 error 时连接仍可用；请求损坏或无法关联时连接关闭。这是本工程的处理选择。对真实写操作不能因重连就自动重试，必须查幂等请求或实际执行结果；本例只有只读能力。

## 实际运行失败路径测试

在本工程终端执行：

```powershell
& ..\..\..\.venv\Scripts\python.exe -m pytest tests -q
```

`-m pytest` 用共享解释器启动测试模块，tests 仅指本单元目录，-q 精简输出。作者当前 40 项通过，其中实际启动受控临时假服务，分别制造 stdout 日志污染、错误 ID、同时 result/error、进程退出、5 秒等待和超长输出；客户端会关闭自己的进程。

临时假服务只在测试创建的目录运行，不调用外网、不读取用户资料。不要把未知服务命令复制到测试里。若 pytest 未安装，按共享环境规则先核查、提出方案并获批，不另建环境或全局安装。

## 练习与答案

### 跟做：清单过滤与调用拒绝

提示：二者都要观察。完成标准是 guest 列表不含内部工具，直接调用仍拒绝，内部 URI 同样拒绝，进程退出。

> [!example]- 参考答案与解析
> 清单只影响发现，执行前检查才保护读取路径。成功关闭进程说明连接资源已回收，不代表数据访问认证已经适合生产。

### 独立：clientInfo改为admin

阅读对应测试，不改启动配置，解释预期结果。完成标准是仍拒绝，并说明不能使用自报元数据作权限依据。

> [!example]- 参考答案与解析
> 业务允许范围来自可信宿主设置的 audience。元数据名字仅用于显示/诊断；若根据 clientInfo.name 授权，任意调用者都可伪造名称。

### 迁移：提交操作响应丢失

假设真实服务提交了订单但客户端超时，能否立刻重试？提示：区分只读与写副作用。完成标准是给出查询/幂等/人工核查步骤。

> [!example]- 参考答案与解析
> 超时不证明提交失败。先按幂等 ID 查外部状态或人工核查，确定结果再决定恢复，不能因重连自动重复提交。本单元未实现提交或外部幂等系统。
""",
    )
    lesson(
        5,
        r"""
## 本讲要解决的问题与前置

学会连接后，还需决定什么时候值得使用 MCP。单个内部函数是不是一定要包装成服务？本讲对照直接调用与 MCP 返回的同一记录，再整理验收报告。

前置是五讲及 [[../../11_LLM_API与Prompt/00 LLM API 与 Prompt 学习地图|模型 API 与结构化消息]]、[[../../15_工具调用协议与工具设计/00 工具调用协议与工具设计学习地图|工具设计]]。当前不调用任何模型 API，不要求 API key。

## Function Calling与MCP在不同层工作

直接函数调用是 Python 程序执行自己的函数，例如 read_record(PUBLIC_URI)。Function Calling 通常指模型接口允许模型返回结构化的工具名和参数，应用再验证并执行工具；模型生成参数不等于已执行。

MCP 为应用和工具服务提供发现、调用及上下文接口。宿主可以把 MCP 工具描述转换为自己模型接口需要的 Schema，把模型建议的调用经过允许范围检查后交给 MCP 客户端；工具结果再作为资料传回模型。这中间的转换、允许范围、费用和失败处理仍需应用负责。

因此 MCP 不替代模型 API，Function Calling 也不替代跨应用服务发现。同一个工具既可在单进程直接调用，也可经 MCP 提供。是否增加协议层，要看复用和隔离边界，而不是因为名字热门。

## 最小示例：对照业务结果

工程新建 `lesson_06.py`：

```python
from catalog import PUBLIC_URI, read_record
from client import StdioClient

direct_record = read_record(PUBLIC_URI)
with StdioClient() as client:
    remote_result = client.request("tools/call", {
        "name": "get_policy", "arguments": {"topic": "refund"}
    })
    assert remote_result["isError"] is False
    remote_record = remote_result["structuredContent"]
print("同一合成业务记录：", direct_record == remote_record)
print("协议调用额外带状态：", remote_result["resultType"])
```

运行 `& ..\..\..\.venv\Scripts\python.exe lesson_06.py`，预期 True、complete。assert 是检查必须满足的条件，失败时停止，不把错误 result 当业务成果。不要用 Python 的优化模式运行来关闭教学断言。

## 一步一步比较

直接调用在当前进程读固定夹具，得到业务字典。MCP 调用在另一个进程读取同样夹具，外层带协议类型、内容块与错误状态，内层 structuredContent 才是同一业务记录。

这个比较只证明当前合成输入的内容一致，不测额外进程/序列化的性能，也不证明任何外部客户端互操作成功。把协议外层和业务内层分开，才能复用业务函数而不让业务层知道所有传输细节。

## 选择表：写明理由

| 情况 | 可以先选什么 | 需要承担的工作 |
| --- | --- | --- |
| 单个 Python 应用调用少量内部函数 | 直接函数封装 | 参数、业务错误、权限及测试 |
| 多个不同应用需要发现并复用同一组能力 | MCP 服务 | 版本/传输、描述、权限、生命周期、部署 |
| 模型要选择工具和参数 | 模型接口的结构化工具机制 | 模型输出校验、预算、允许范围和执行 |
| 远程、多用户、受限制系统 | 另行设计真实服务与授权 | 认证、OAuth/凭据、TLS、租户、审计和运维 |

使用 MCP 的具体收益是复用协议入口；直接函数的具体收益是少一层连接和消息处理。不能只回答“MCP更专业”。每项方案都要说明输入、输出、失败、维护成本及边界。

## 完成单元验收

先运行完整演示，新文件名避免覆盖学习记录：

```powershell
& ..\..\..\.venv\Scripts\python.exe demo.py --output report-my-01.json
& ..\..\..\.venv\Scripts\python.exe -m pytest tests -q
& ..\..\..\.venv\Scripts\python.exe -m ruff check .
& ..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

--output 指定报告路径，以工程当前目录为基准；文件存在会拒绝覆盖，改新名字。pytest 检查行为，Ruff check 检查规则，format --check 检查格式但不修改文件；三者用途不同。

报告应显示新版协议、reader 两个工具/guest 一个、非法参数 -32602、工具权限 isError=True、资源拒绝码1001、资料不可用 isError=True、参数错误后连接仍可用、所有自有子进程退出。llm_called 与 external_application_connected 都是 False。

再写自己的验收页：角色/传输/协议版本、三类能力、Schema和合法参数、正常资料及来源、两类错误、隐藏工具直接拒绝、固定URI边界、超时和关闭、MCP与直接函数选择、未做的真实认证/SDK互操作/模型接入。

作者实现并测试的是有限标准消息子集，未安装官方 MCP SDK，未使用外部宿主或 Inspector 做互操作验证。不同真实宿主可能要求完整能力、旧版回退或额外传输；需要具体需求再提出 SDK/工具安装方案，不能把“单元示例通过”写成“所有 MCP 客户端兼容”。

## 常见错误与排查

直接比对 remote_result 与 direct_record：一个带协议外层，先取 structuredContent。只测试 happy path：要运行拒绝和故障样例。格式检查通过就写运行成功：它没有执行服务。读到新版规范却沿旧 initialize 调用：核对版本和实现，当前明确拒绝旧握手。

不要在本轮练习中复制陌生“全权限文件系统服务”命令、填真实密钥或连生产业务；本节产物是可检查的本地教学服务。新增真实接入属于明确需求、环境与授权的后续工作。

## 练习与答案

### 跟做：记录同一业务与不同外层

提示：画两个字典的层次。完成标准是 True/complete，并说明 remote_result 多了什么，哪部分参与业务比较。

> [!example]- 参考答案与解析
> direct_record 是业务记录；remote_result 含 resultType、content、isError、structuredContent 等，比较的是 structuredContent。传输相同内容不自动证明协议全功能或性能。

### 独立：为个人小脚本选方案

只有一个 Python 程序读两份固定文件，暂不需要其他应用发现。选择并解释。完成标准是考虑复用需求、连接成本和未来扩展。

> [!example]- 参考答案与解析
> 先保留职责清晰的普通函数即可，做好校验与测试。出现真实跨应用复用需求，再把同一业务函数包成服务，而不是先增加大量进程和配置。

### 迁移：接入真实获批宿主

列一张接入计划，不执行未知安装。完成标准是写宿主支持版本、传输、SDK版本/依赖、最小允许范围、测试及回退。

> [!example]- 参考答案与解析
> 先核对宿主支持新版还是旧握手、stdio还是HTTP，再选匹配实现；说明下载/安装位置和影响，获批后安装。只开放必要只读能力，做发现/调用/错误/拒绝/关闭与宿主实际互操作，保存版本和失败记录。真实多用户还需身份授权，不能用演示 audience 代替。

## 返回与后续

[[../参考工程验证记录|作者实际结果和未测范围]] · [[../示例工程/README|代码导航]]。下一单元规划：推理与工具数据构造，待编写。
""",
    )
    write(
        f"{MAP}.md",
        r"""
## 第一步做什么

打开 [[逐讲学习/01 认识MCP并区分工具资源与提示|第 1 讲]]，在 VS Code 创建 lesson_01.py，用根共享解释器运行。完成判断：能指出请求 ID、JSON-RPC 版本与 MCP 版本，说明“构造消息”还没有执行工具。

## 六讲学习顺序

1. [[逐讲学习/01 认识MCP并区分工具资源与提示|01 认识角色与三类能力]]
2. [[逐讲学习/02 用stdio连接本地服务并发现能力|02 连接并发现能力]]
3. [[逐讲学习/03 按Schema调用工具并读懂两类错误|03 调用工具与区分错误]]
4. [[逐讲学习/04 读取固定资源并获取提示模板|04 读取资源与取提示]]
5. [[逐讲学习/05 验证权限拒绝超时与连接回收|05 验证拒绝与连接回收]]
6. [[逐讲学习/06 比较MCP与直接函数调用并完成验收|06 选择方案并验收]]

## 前置与阅读方式

[[../15_工具调用协议与工具设计/00 工具调用协议与工具设计学习地图|字典与工具契约]]、[[../18_后端网络与系统设计/00 后端网络与系统设计学习地图|消息与服务]]、[[../21_Agent安全与执行边界/00 Agent安全与执行边界学习地图|权限边界]]。陌生语法先沿链接复习；stdio/子进程/EOF在本单元解释。

Obsidian 读正文，VS Code 看 [[示例工程/README|源码导航]]。本机例子只需标准库与共享环境已有 pytest/Ruff，不安装 SDK，不创建单元虚拟环境，不使用模型或 GPU。

## 本单元产物与边界

一组真实本地 stdio 请求响应：新版能力发现、工具查询、资源读取、提示准备、参数与权限拒绝、故障与自有进程回收。资料与 reader/guest 范围全部合成。

2026-07-28 为核对采用的规范版本；本工程有限子集，不是完整 SDK 或全协议符合性认证。没有旧版回退、HTTP/OAuth、外部宿主互操作、模型接入、订阅、通用分页/缓存/Schema验证或写操作。[[参考工程验证记录|作者结果]]不能替代自己的练习记录。

[[../../00 从这里开始|学习首页]] · [[../我的学习记录|记录亲自学习结果]]。

下一单元规划：推理与工具数据构造，待编写。
""",
    )
    write(
        "示例工程/README.md",
        r"""
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

[[../00 MCP与工具生态学习地图|六讲正文]] · [[../参考工程验证记录|作者实际验证与限制]]。
""",
        "MCP示例工程代码导航",
    )
    print("已写入单元30六讲、地图及工程导航")


if __name__ == "__main__":
    main()
