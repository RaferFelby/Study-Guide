"""编写本机流式服务教材；测试与实验另行执行。"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "01_学习指南/27_推理服务与性能工程"
MAP = "00 推理服务与性能工程学习地图"
LESSONS = [
    "01 让客户端逐段收到推理输出",
    "02 校验请求并限制同时生成数量",
    "03 取消生成并释放断开请求",
    "04 测量首段延迟吞吐与分位数",
    "05 理解连续批处理与KV分页",
    "06 比较量化质量并完成服务报告",
]


def write(name, body, title=None):
    path = ROOT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\ntitle: {title or path.stem}\ntags: [learning, serving, performance]\nupdated: 2026-10-11\n---\n\n# {title or path.stem}\n\n"
        + body.strip()
        + "\n",
        encoding="utf-8",
    )


def lesson(index, body):
    previous = (
        f"[[{LESSONS[index - 1]}|上一讲]]"
        if index
        else "[[../../26_SFT与LoRA全流程/00 SFT与LoRA全流程学习地图|前一单元]]"
    )
    following = (
        f"[[{LESSONS[index + 1]}|下一讲]]" if index < 5 else f"[[../{MAP}|返回地图]]"
    )
    write(
        f"逐讲学习/{LESSONS[index]}.md",
        f"[[../{MAP}|单元地图]] · {previous} · {following}\n\n" + body,
    )


if __name__ == "__main__":
    lesson(
        0,
        r"""
## 本讲要解决的问题与前置

一次生成要等几秒才全部结束，用户却希望先看到第一部分。本讲搭建真实HTTP流式接口；后端用可控延迟生成“片段1、片段2”，学习协议和计时，不声称它是大语言模型推理。

前置：[[../../18_后端网络与系统设计/00 后端网络与系统设计学习地图|HTTP与客户端服务端]]、[[../../24_FDE需求协作演示与交付/00 FDE需求协作演示与交付学习地图|本机服务与模拟边界]]。需要会JSON、字典和终端运行，不默认懂SSE。快速顺序：理解事件 → 启动服务 → 运行客户端 → 看解析 → 做练习。

## 概念与直觉：一次响应，多个事件

SSE是Server-Sent Events，服务端向客户端持续发送文本事件。HTTP连接保持到这一响应结束，客户端不用每个片段重新发请求。这里通过POST提交任务，再读取其SSE响应；浏览器原生EventSource通常发GET，因此不能把本例POST直接塞进EventSource。

一个事件包含 `event: delta` 和 `data: {...}` 两行，最后一条空行表示事件结束。delta是本工程的“新增片段”名称；done是结束事件，error是故障。它们属于我们约定的schema，不意味着兼容任意厂商模型接口。

像分段送菜：上第一道时无需等全部菜。但实际机制是服务端写入字节并flush，网络与客户端解析共同影响可见时间；类比不代表每个网络包就是一道完整事件。[SSE标准](https://html.spec.whatwg.org/multipage/server-sent-events.html)定义了文本解析规则。

## 最小操作：两个终端

在VS Code打开 `示例工程`，选择根目录共享.venv。终端A运行：

```powershell
& ..\..\..\.venv\Scripts\python.exe server.py --port 8770 --capacity 2
```

port是本机监听端口，capacity表示最多2个后端生成，不是最多2条网络连接。正常打印 `http://127.0.0.1:8770`；127.0.0.1只指本机，不是公开上线。终端A保持运行。

新建终端B，同样进入示例工程：

```powershell
& ..\..\..\.venv\Scripts\python.exe client.py --output-units 8
```

预期逐段显示片段1至8，随后JSON中success为true、output_units为8。模拟每片段设置6毫秒等待，但系统定时与调度可能使实测更长；字符并不是实际模型Tokenizer的token。

## 最小Python客户端与逐步讲解

工程新建 `lesson_01.py`：

```python
from client import stream_request

def show_piece(event):
    print(event["text"], end="", flush=True)

result = stream_request("http://127.0.0.1:8770", output_units=4, on_delta=show_piece)
print("\n成功：", result["success"])
print("输出片段数：", result["output_units"])
```

执行 `& ..\..\..\.venv\Scripts\python.exe lesson_01.py`，应显示四个片段与True/4。show_piece是回调，即函数在每段到来时被客户端调用；不要写成 `on_delta=show_piece()`，那会提前执行而不是交给客户端稍后调用。

stream_request先组装JSON与唯一request_id，再发请求，检查响应为text/event-stream。read_events逐行累计data，到空行才解析JSON。注释心跳不当成输出；每事件ID与片段顺序都校验。必须读到finish_reason为stop的done且数量吻合才算成功。连接断了即使已经显示一些文字，也不能默认为完整成功。

服务器flush只是请求尽快送出数据，不保证网络、代理或UI即时显示。本例没有反向代理；迁移时需检查缓冲、超时和客户端读取方式。WebSocket支持双向长期交互，本例只需服务端逐段输出和单独取消接口，无需先引入它。

## 常见错误与练习

连接拒绝：先看终端A是否运行、端口是否8770。端口被占：选8771并同时改客户端address，不停止不明程序。输出一次性出现：检查是否使用一次read读全响应、是否flush；终端排版与网络缓冲也可能影响。

### 跟做：输出4个片段

运行上例并记录success与实际文字。完成标准是4段、True，能说出done的用途。

> [!example]- 参考答案与解析
> done明确任务正常结束；EOF仅意味着连接结束，两者不能混用。四个delta加一个合法done才满足本例契约。

### 独立：解释事件边界

如果一个事件data跨两行，能每行单独json.loads吗？

> [!example]- 参考答案与解析
> 不能。先按事件收集data并用换行连接，到空行再解析。本例测试有跨行JSON；网络包还可能把任意一行拆成多个字节片段。

### 迁移：真正模型接入

列出后端替换后需核对的四项。

> [!example]- 参考答案与解析
> 模型/Tokenizer版本、实际token边界与用量、取消/停止原因、事件schema和错误语义。先核对依赖/设备方案，不把模拟睡眠吞吐当模型吞吐。
""",
    )

if __name__ == "__main__":
    lesson(
        1,
        r"""
## 本讲要解决的问题与前置

如果请求要求无限输出、客户端重复提交、同时超过承载量，服务该怎样回答？本讲分清请求校验、接纳限制与身份。前置是上讲服务已启动；读server.py的validate_request、ServiceState、Handler。

快速顺序：手算合法请求 → 执行校验 → 看状态码 → 看容量槽 → 检查边界。必须掌握输入范围和容量；生产认证、网关及全局连接限制留迁移设计。

## 请求模型：先约定字段，再执行

本例生成请求恰有prompt、output_units、request_id三个字段。prompt去除两端空白后需1～512字符；output_units是1～32的整数，True虽在Python中表现像整数也被明确拒绝；request_id是1～64位字母、数字或连字符。额外role/admin字段不会被接受。

请求body最多4096字节，content-type需application/json。字符长度和UTF-8字节长度不同，两个上限解决不同问题。校验必须在占用后端槽之前完成，不能先启动昂贵生成再检查长度。

## 最小示例：不联网看输入校验

工程内新建 `lesson_02.py`：

```python
from server import validate_request

body = {"prompt": "toy input", "output_units": 4, "request_id": "lesson-02"}
print(validate_request(body))
try:
    validate_request({**body, "output_units": True})
except ValueError as error:
    print("已拒绝：", error)
```

执行 `& ..\..\..\.venv\Scripts\python.exe lesson_02.py`，第一行返回原合法字典，第二条显示拒绝output_units。`{**body, ...}`先复制body条目，再用同名键覆盖；不会改变原字典。try/except只处理本次已预期校验错误，不是对所有异常一律打印成功。

## 状态码与实际接纳流程

400表示参数/JSON有问题；415表示内容类型不接受；413表示body大小不符合约定；409表示相同活动request_id重复；429表示当前后端槽满。它们发生在流式头之前，客户端可以按HTTP错误记录。请求已返回200并进入流后发生后端错误，用error事件表示；200不能保证整个流成功。

ServiceState用BoundedSemaphore表示容量槽：进入生成先非阻塞获取，满了立即429，结束在finally归还。Bounded表示不能把槽归还到初始数量以上，能暴露重复释放。锁保护活动字典及计数，避免两个线程同时通过相同request_id检查。

本例不排队、不自动重试。Retry-After:1只是忙时建议等待至少一秒后由客户端决定，不代表一定可成功。实际重试还需退避、总时间预算和幂等语义；不要由20个客户端毫无间隔地一起重试。

## 并发限制的边界

ThreadingHTTPServer为请求使用线程，这让流式输出时仍能处理取消。capacity只限制已接纳的后端生成；它没有限制全部HTTP线程、连接、请求到达速率或操作系统资源。因此仅本机演示，不是抵抗公网洪泛的服务。

X-Demo-Session是公开模拟会话标记，用来演示“取消只能针对相同会话”，任何本机调用者都可以写它，不是真实身份认证。生产需要受信身份体系、授权、TLS、限流、队列/线程边界和指标权限；不能把演示header叫安全令牌。

FastAPI可以用请求模型自动执行很多字段校验，StreamingResponse承载生成器输出，但仍需实现容量、取消和业务错误语义。本工程使用标准库以避免新增依赖，未部署FastAPI。[FastAPI官方响应说明](https://fastapi.tiangolo.com/advanced/custom-response/)供后续迁移核对，不把框架名称等同于全部可靠性。

## 动手与预期

把output_units改成33运行上例应拒绝，恢复4应通过。在终端B运行benchmark的并发4命令前先记下服务capacity2，预测可能出现429；第4讲再测分母。查看GET /stats中的active，不应长期超过2。重复ID保护只作用于活动请求，完成后的ID不是永久去重或持久幂等系统。

## 常见错误与练习

流已开始才改状态码：HTTP头已发送，改用受控error结束并记录。429当模型质量失败：区分服务接纳失败与内容评估失败，但请求失败分母仍包含它。认为capacity=2只能连接2人：澄清后端槽与线程边界。

### 跟做：三个非法输入

尝试空prompt、33输出、request_id含斜杠。完成标准是三项都拒绝并说出哪个限制触发。

> [!example]- 参考答案与解析
> 分别文本范围、整数范围与ID字符范围。非法输入不进入backend.generate，因此没有后端资源分配。

### 独立：200之后失败

后端抛错时客户端怎样判断成功？

> [!example]- 参考答案与解析
> 必须检查error/done事件、结束原因与实际数量；只看HTTP200会错误统计。服务器应记backend_failed并释放槽，不能把部分输出算完整任务。

### 迁移：何时加队列

写出至少三个队列决策条件。

> [!example]- 参考答案与解析
> 最大排队数量、队列等待时间预算、取消能否删除未执行任务；同时说明过期/满时拒绝和业务优先级。无边界队列只是把过载延后变成更大延迟。
""",
    )

if __name__ == "__main__":
    lesson(
        2,
        r"""
## 本讲要解决的问题与前置

用户已取消，后台却仍生成，资源会被白白占用。本讲验证取消、断开和finally释放。前置：第2讲的request_id、模拟会话与容量槽；读backend.py的Event.wait、server.py的异常边界及demo.py。

## 概念与直觉：提出取消，不是瞬间删除线程

threading.Event是线程可共享的信号。cancel接口找到活动请求、检查会话，设置Event；后端在等待和每段生成边界检查信号，发现后抛GenerationCancelled，响应结束并在finally释放槽。

这叫协作式取消：执行者主动检查。Event不能强制杀死正在不可中断调用里的线程，也不能使已经送出的网络字节消失。真实GPU/远程模型需要接入它自身的abort或取消机制；只取消客户端future不证明远端计算停了。

## 最小示例：第一段后提出取消

保持server.py运行，工程新建 `lesson_03.py`：

```python
from client import stream_request
from demo import cancel_request

address = "http://127.0.0.1:8770"
def cancel_first(event):
    if event["unit_index"] == 0:
        code, body = cancel_request(address, "lesson-cancel")
        print("取消响应：", code, body["status"])

result = stream_request(address, request_id="lesson-cancel",
                        output_units=16, on_delta=cancel_first)
print("完整成功：", result["success"])
print("已收到片段：", result["output_units"])
```

执行 `& ..\..\..\.venv\Scripts\python.exe lesson_03.py`，通常取消202/cancel_requested、完整成功False、片段少于16。网络与线程竞争可能已有第二段被写出，因此不能要求“永远恰好一段”。202表示已接纳取消请求，真正释放需查看活动状态与后端结束记录。

## 逐步执行与状态检查

客户端在收到第0个delta后调用回调；回调发一个独立HTTP取消请求。服务的另一线程检查相同demo-a会话并set信号。SyntheticBackend使用 `cancelled.wait(delay)`：等待期间若信号出现会提前返回True，比普通sleep之后才检查更及时。

服务发送finish_reason为cancelled的done；客户端仍记 `cancelled_or_incomplete`，不把用户主动取消混为后台未知异常。服务端计数cancelled，active应很快回0；新的正常请求应可使用释放槽。

取消已经完成的ID返回404；其他模拟会话取消活动ID返回403；正在活动的同会话返回202。活动字典只保留进行中的任务，不是长期任务状态数据库。实际生产认证必须来自可信身份，不信客户端自由填写的session。

## 断开和后端故障

客户端直接关闭连接时，服务在下次写入可能收到BrokenPipeError或ConnectionResetError，设置取消信号并记disconnected，finally释放。不能保证断开瞬间被发现；系统缓冲可能延迟识别。测试使用本机TCP复位，验证明确断开路径，并检查槽释放。

后端未知异常在请求边界记录错误堆栈、发送受控error，不向客户端泄露异常文本，并记backend_failed。这里宽泛异常捕获只作用于单次请求边界，失败明确可见；数据清理和核心算法中不能照搬“所有异常都忽略”。

finally表示无论正常、取消、断开、异常都执行收尾。reserve成功一次，就必须finish一次；未成功取得槽的请求不能释放。运行演示的上下文退出也会设置所有取消信号并检查active为0，防止作者脚本留下后台任务。

## 动手、常见错误与练习

运行取消例子后，在终端B再运行正常client.py。应成功输出8片段。若一直429，查看active与finish逻辑是否遗漏；不要重启掩盖泄漏后称取消有效。接口取消202但active不降，应检查后端是否真正读取Event，而不只是设置了变量。

### 跟做：取消后再请求

记录取消202、False、已收到片段及后续正常True。完成标准包括资源可再次使用。

> [!example]- 参考答案与解析
> 取消请求被接纳只验证控制路径；后续正常成功及active归零验证收尾路径。片段数量允许调度差异，但不能完整16段仍称取消及时有效。

### 独立：解释finally放哪里

reserve被拒绝与reserve成功后抛错，各怎样释放？

> [!example]- 参考答案与解析
> 拒绝时没取得槽，不释放；成功后进入try/finally，异常也finish。重复释放会让BoundedSemaphore报错，不能吞掉来伪造稳定。

### 迁移：远程模型取消

本地用户取消后只停止显示，够不够？

> [!example]- 参考答案与解析
> 只停止显示会继续耗远端算力/费用。需调用后端abort或关闭它支持的取消通道，记录是否实际停止及部分计费；无法确认时写“客户端停止读取，远端取消未验证”。
""",
    )

if __name__ == "__main__":
    lesson(
        3,
        r"""
## 本讲要解决的问题与前置

“响应很快”需要用数据说明：第一段多久出现？完成多久？并发增加后有多少失败？前置是前三讲能正常生成和取消。读client.py的时间点、percentile和benchmark.py。先固定条件再计时，不先追求某个漂亮数字。

## 概念与指标：先给每个时间点命名

客户端在发请求前记t0，第一段记t1，最后一段记t_last，合法done完成记t_done。TTFT通常指time to first token，首token时间；本模拟没有真实token，所以字段ttft_seconds测的是第一输出片段到达时间。

TPOT是time per output token，输出token间平均时间；本例为 `(t_last-t1)/(片段数-1)`，只表示片段平均间隔。仅一段时没有间隔，返回None，不能写0。完成延迟为t_done-t0，包含请求建立、排队/接纳、后端、网络及解析。

吞吐为完整成功请求产生的总片段数除整批墙钟秒；不是把每请求的片段/秒平均。失败率为失败请求数/发起请求数，429、连接错误、缺done和取消都不能伪装成功。用户取消与异常在原始记录中分类，但本次完整完成率都不计成功。

真实模型需要匹配Tokenizer和后端计量，有些SSE事件含多个token，所以“事件数=token数”不成立。[vLLM指标文档](https://docs.vllm.ai/en/latest/design/metrics/)可供实际接入时核对服务端定义；服务端TTFT与客户端含网络TTFT也应分别命名。

## 最小示例：分位数不是平均数

工程新建 `lesson_04.py`：

```python
from client import percentile

latencies = [0.1, 0.2, 0.3, 1.0]
print("P50：", percentile(latencies, 0.5))
print("P95：", percentile(latencies, 0.95))
```

执行 `& ..\..\..\.venv\Scripts\python.exe lesson_04.py`，预期0.2和1.0。本工程用nearest-rank：排序后取第ceil(p×N)项，Python下标再减1；不是插值法，所以其他库算法可能不同。P95表示按这个有限样本定义的位置，不是95%的请求都恰好这么慢。N=4时P95就是最大值，不能稳定估计尾部。

## 动手压测：同一服务、三种并发

终端A保持capacity2。终端B依次执行，每个文件名必须未存在：

```powershell
& ..\..\..\.venv\Scripts\python.exe benchmark.py --requests 20 --concurrency 1 --output report-my-c1.json
& ..\..\..\.venv\Scripts\python.exe benchmark.py --requests 20 --concurrency 2 --output report-my-c2.json
& ..\..\..\.venv\Scripts\python.exe benchmark.py --requests 20 --concurrency 4 --output report-my-c4.json
```

requests是20个计入测量的请求；concurrency是最多同时工作的客户端线程；每条固定8个空格词输入、目标8输出片段。每批先预热1次且明确排除在20个分母外。没有自动重试；4线程可能迅速反复发送新任务并收到429，因此不是固定到达率、固定QPS的压测。

闭环表示线程完成一个请求后再处理下一任务，拥堵会降低实际发送速率；开放环以独立时间表发请求，容易看到持续积压。当前只实现闭环有限压测，不把它写成生产容量上限。真实负载还需长度分布、突发、到达速率、持续时间及冷启动另测。

## 预期与逐步读报告

作者一次结果：并发1/2各20成功、0失败；并发4只有4成功、16个429，失败率80%。成功片段吞吐约40.5/72.8/46.0片段每秒；完成P95约0.174/0.193/0.366秒。自己的数字允许变化，负载、操作系统和调度都会影响，不能把作者数字复制成个人实测。

先看conditions和scope，确认实际HTTP与模拟后端；再看successes+failures是否等于20；接着看results的failure原因；最后看成功请求延迟。分位数仅基于成功请求，失败请求不能从总分母消失。若全失败，成功延迟为null而不是0毫秒。

environment里GPU为not_used、peak_memory为null。不是显存0，而是没有用GPU也未测进程峰值内存。真实模型报告需注明显卡、权重精度、输入输出token长度、batch/并发、采样设置、KV缓存与实际显存口径，再比较任务质量。

## 常见错误与练习

把8片段当8模型token：改名称与计量来源。P95只报不写N：加样本数和算法。全失败还报低延迟：报告失败率及null成功统计。用20/总时间算token吞吐：分子应实际完成输出量，不是请求数。output文件已存在：换新名字保留旧记录。

### 跟做：核对分母

打开三份自己的报告，分别算successes+failures。完成标准是每批20，预热另列1。

> [!example]- 参考答案与解析
> 失败不会被重新提交来凑20条成功。本协议是20次尝试；若改成20次成功加重试，分母、总成本与负载都会变化，必须另写协议。

### 独立：计算吞吐

5个完整请求各输出4单位，另2个失败，总墙钟2秒，按本例口径是多少？

> [!example]- 参考答案与解析
> 20/2=10单位每秒，失败率2/7。失败请求部分输出不计完整任务吞吐，原始结果仍保留其输出数量，不删掉。

### 迁移：比较两个模型

列出必须相同或明确记录的条件。

> [!example]- 参考答案与解析
> 硬件、输入/输出实际token长度与Tokenizer、并发和负载模式、采样、预热、模型权重精度、成功判断与任务质量；不同Tokenizer单位不能简单按字符数换算。先定义业务可接受失败率与延迟，再谈吞吐。
""",
    )

if __name__ == "__main__":
    lesson(
        4,
        r"""
## 本讲要解决的问题与前置

真实推理服务为什么需要专门引擎，而不是为每请求开一个线程就够了？本讲解释prefill、decode、KV缓存、连续批处理和分页。前置是第4讲并发与指标，以及 [[../../08_Transformer从零实现/00 Transformer 从零实现学习地图|注意力]]。这讲运行离散模拟，不安装vLLM、不做GPU内核性能声明。

## Prefill、decode与KV缓存

prefill是先处理已有提示，把各位置的表示和注意力所需状态算好；decode是反复生成下一token。KV是注意力的Key、Value，即键和值张量；历史位置的K/V可缓存，之后新token通常不用重算所有历史K/V。

缓存仍要读历史内容，序列越长读取与存储压力越大。第26单元TinyLM每步重算整个前缀，没有KV缓存，因此不能用它的小模型时间推断工业服务性能。线程并发只描述CPU任务调度，不自动实现GPU批处理或KV共享。

先用自己的形状推导估算：KV元素量约 `2×层数×序列长度×KV头数×每头维度×批量`，再乘每元素字节。2来自K与V。假设2层、10位置、2个KV头、头维4、批量1、每元素2字节，约640字节；这是虚构尺寸的算术，不含对齐、碎片和引擎状态。GQA模型KV头数可能少于查询头数，应读真实配置而不机械用总attention heads。

## 静态批与连续批：看空槽何时补入

静态批等待整批请求都结束后再接下一批；短请求完成后可能留下空槽。连续批在生成轮次之间移除完成请求、补入可执行新请求，提高不同长度工作负载下的利用率；调度还需要公平、容量及prefill与decode竞争处理。

本模拟容量2，A/B在第0轮到达，长度2/5；C在第1轮到达，长度1。每轮每请求处理一个单位，结束时间按轮次边界计。工程新建 `lesson_05.py`：

```python
from scheduler import simulate_schedule, page_allocation

print("静态完成：", simulate_schedule(False)["completed_tick"])
print("连续完成：", simulate_schedule(True)["completed_tick"])
print("分页：", page_allocation([5, 2], block_size=4))
```

执行 `& ..\..\..\.venv\Scripts\python.exe lesson_05.py`，静态A2/B5/C6，连续A2/C3/B5。C到达1，静态等待加执行5轮，连续2轮；不是“vLLM提升2.5倍”的测量。trace里静态A结束后仍占批槽直到B结束，但不继续生成token；连续立即让出槽。

## PagedAttention：逻辑连续，物理不必连续

假设每缓存块存4位置，长度5需要2块、长度2需要1块，共3块12位置，使用7个、余5个。固定给两请求各预留最大16位置会预留32位置，空间利用不同；真实系统还考虑块管理开销和复用，不能从这个例子证明具体GPU节省百分比。

逻辑块0/1是请求顺序中的编号，物理块是显存池中实际位置。例如请求A的逻辑块映射到物理块3/8，请求B到块1；索引表记录映射，内核按表读取。分页让分配不必为每请求寻找一大段连续空间，完成后块可归还再分配。

[PagedAttention论文](https://arxiv.org/abs/2309.06180)与 [vLLM实现说明](https://docs.vllm.ai/en/latest/design/paged_attention/)是后续深入依据。scheduler.py只计算块数，不存K/V、不运行该注意力内核、不提供共享前缀。前缀缓存还需确认相同模型、模板与token；多租户必须有授权隔离、生命周期和容量边界，不能为复用速度跨用户暴露私有上下文。

## 动手与采用边界

分别打印两个trace，每行写出tick与占用的请求，解释C为什么可提前。把page_allocation的长度改为[4,4]，应2块8位置、余0；改为[5,5]应4块16位置、余6。块大可降低索引开销却增内部浪费，这只是机制权衡，最佳值需真实引擎测量。

若未来部署vLLM，先核对操作系统/设备、模型架构/权重格式、显存、版本、安装和下载规模，遵守共享环境审批。本单元不提供未经本机验证的安装命令，模拟与真实后端性能记录分开保存。

## 常见错误与练习

SSE流式就叫连续批：SSE只是传输，连续批是后端调度。KV缓存叫“缓存答案”：它缓存张量状态，不是数据库里的完整文本结果。分页认为零浪费：最后块仍可能空槽。头数选错：核对KV heads而不是query heads。

### 跟做：解释C完成轮次

完成标准是能指出A在第2轮边界让出槽，C第2轮进入、边界3完成。

> [!example]- 参考答案与解析
> B仍在执行，不需等到边界5；静态批则到5才让C进入，6完成。这个模拟不考虑真实prefill成本和GPU执行差异。

### 独立：长度9、块4

求块数、分配位置、浪费。

> [!example]- 参考答案与解析
> ceil(9/4)=3块，分配12，未用3。仅按位置数量，不含块表和dtype字节开销。

### 迁移：长短请求公平

只优化总吞吐有什么风险？

> [!example]- 参考答案与解析
> 长请求可能长期占容量、短请求首token等待变长；反向偏好短请求也可能让长请求饥饿。需要同时记录TTFT/P95、长度切片、拒绝率、公平及任务质量，不能单看总体吞吐。
""",
    )

if __name__ == "__main__":
    lesson(
        5,
        r"""
## 本讲要解决的问题与前置

更低位宽可能节省模型权重，但质量和实际速度怎样判断？本讲做可运行INT4算术，再写服务报告。前置是第4讲指标和 [[../../26_SFT与LoRA全流程/00 SFT与LoRA全流程学习地图|参数、精度与任务对照]]。量化的真实大模型部署仍为选修，不在未批准时安装量化库。

## 概念与直觉：用少量刻度表示数值

量化把浮点数近似为有限整数刻度。对称INT4教学例使用-7至7及一个scale，`整数 = round(权重/scale)`，恢复 `整数×scale`。本例未用-8刻度，这是方便对称演示的选择，不是所有INT4格式的唯一标准。

例如权重[0.31,0.89]，scale=0.89/7≈0.12714，整数[2,7]，恢复[0.25429,0.89]。第一项发生误差，第二项正好落最大刻度。真实实现还需分组、尺度存储、打包与算子支持；Python整数列表没有实际压成4位，也没有GPU加速。

## 最小示例：任务决策会翻转

工程新建 `lesson_06.py`：

```python
from quantization import compare_task

report = compare_task()
print(report["quantization"])
print("原始通过：", report["fp_passed"], "/", report["n"])
print("INT4通过：", report["int4_passed"], "/", report["n"])
for case in report["details"]:
    print(case["inputs"], case["fp_passed"], case["int4_passed"])
```

执行 `& ..\..\..\.venv\Scripts\python.exe lesson_06.py`。预期原始4/4，INT4为2/4；这4条是固定二维线性阈值算术Case，不是模型保留评估集，更不是AWQ/GPTQ结果。

## 逐步讲解与误差原因

第一条输入[1,-0.32]：原始点积0.31-0.32×0.89=0.0252，大于零；恢复权重点积0.25429-0.2848≈-0.0305，小于零，分类翻转。接近阈值时小权重误差可能改变任务结果，因此只看平均数值误差或perplexity不足以判断业务风险。

perplexity是由语言模型平均预测损失换算的困惑度，可衡量下一token预测，但不是工具参数合法性、引用正确性或业务成功。真实量化前后必须用相同任务Case、同解码配置和独立保留集对照，报告失败类别。

AWQ侧重利用激活统计判断重要通道并调整缩放；GPTQ用近似二阶信息降低权重量化误差。它们不是将所有权重简单round就完成的算法。本例不实现它们，参考 [AWQ论文](https://arxiv.org/abs/2306.00978)、[GPTQ论文](https://arxiv.org/abs/2210.17323)。校准集用于确定量化参数，也需避免拿测试集校准再声称测试独立。

## 动手：完成一页服务报告

在Obsidian自己的学习记录写以下内容，不把作者数据当个人实测：

1. 目标与范围：本机SSE服务，人工延迟后端，输出单位为片段。
2. 环境与配置：Python/系统、服务capacity2、预填充每单位3毫秒/每片段6毫秒的配置、输入8/输出8单位、并发1/2/4、每批20尝试、预热1排除、无重试。
3. 完成指标：成功/失败总分母、429等失败原因、TTFT/P50/P95/TPOT、完成片段吞吐与墙钟。注明分位数nearest-rank，仅成功请求。
4. 生命周期：取消已接纳是否真的active归零；断开/故障能否释放槽；模拟session不能充当认证。
5. 模型与显存：未用真实模型/GPU，峰值内存未测，不写0。
6. 量化：只做四条算术2/4退化，不采用其替换模型；真实AWQ/GPTQ未实施，列为后续选修及所需批准方案。

判断是否完成：自己能正常流式读取、解释过载分母、复现取消后新请求成功，并能说明模拟与模型性能的差别。终端A用Ctrl+C停止自己启动的服务，不结束不明进程。自动demo.py会临时端口启动、取消并关闭服务，适合作者回归。

## 迁移到真实模型时怎样推进

先用第26单元可信微型权重也可验证模型接口，但它没有通用语言能力和KV缓存；要测工业推理选择适合实际硬件与任务的模型/引擎，准备具体依赖、权重大小、存储和CPU/CUDA方案获得批准后再执行。保持相同HTTP契约或明确改版，重新定义token计量，单列冷启动、预热、不同长度/并发和质量回归。

速度提升却错误率上升时，依据业务阈值拒绝方案或限定适用场景。不要为“完成性能优化”而隐藏退化；这个单元学的是怎样提出可检查的结论。

## 常见错误与练习

整数列表说节省8倍内存：没有打包与尺度开销实测，不成立。校准与测试混用：重建独立测试。量化方法相同却速度不同：核对硬件、内核、批量与KV瓶颈。没有GPU却显存写0：改未使用/未测。

### 跟做：手算第一条翻转

完成标准是算出原始正、恢复后负，解释阈值影响。

> [!example]- 参考答案与解析
> 0.0252变约-0.0305，小误差跨过零决策边界。这不是泛化定理，而是一个具体失败Case。

### 独立：为什么不采用

用本例四条Case写一句准确结论。

> [!example]- 参考答案与解析
> 固定算术集原始4/4、恢复INT4为2/4，本次近似不满足保持该任务质量的要求；没有实际压缩存储/加速证据，不应声称可用LLM量化方案。

### 迁移：量化后服务更快

若吞吐提高但关键工具参数错误新增，怎样处理？

> [!example]- 参考答案与解析
> 保留对照证据、统计关键错误和用户影响；若超过业务失败阈值拒绝替换，尝试更高精度/其他方案再做新验证。真实模型量化是后续任务，不能用本例算术结论代替它。

## 后续

[[../参考工程验证记录|作者验证与未测范围]]。下一单元规划：记忆与上下文管理，待编写。
""",
    )

if __name__ == "__main__":
    write(
        f"{MAP}.md",
        r"""
## 现在学哪一讲

先打开 [[逐讲学习/01 让客户端逐段收到推理输出|第1讲]]，在VS Code的示例工程终端A启动server.py，终端B运行client.py。完成第一步：看到逐段输出和合法done，而不是只看到HTTP200。

## 六讲顺序

"""
        + "\n".join(
            f"{i + 1}. [[逐讲学习/{name}|{name}]]" for i, name in enumerate(LESSONS)
        )
        + r"""

## 前置与操作

[[../18_后端网络与系统设计/00 后端网络与系统设计学习地图|HTTP基础]]、[[../26_SFT与LoRA全流程/00 SFT与LoRA全流程学习地图|模型训练与精度]]；若还不能运行Python，先回 [[../01_Python工程化/逐讲学习/01 认识项目并运行 Python|最初运行步骤]]。讲解在Obsidian，代码在VS Code；全部本机Python使用根目录共享.venv，不新增依赖。

## 产物与完成判断

真实本机HTTP流式接口、请求校验/容量拒绝、取消与断开演练、20次×三并发报告、离散连续调度与KV块数模拟、INT4算术质量对照。模拟后端不生成真实模型token；没有vLLM/FastAPI/AWQ/GPTQ部署，不把片段吞吐写成LLM性能。能解释失败分母、释放生命周期和质量退化才算理解。

[[示例工程/README|代码与命令]] · [[参考工程验证记录|作者记录]] · [[../../00 从这里开始|学习首页]]。自己的实操写个人学习记录，作者通过不代替学习者验收。

下一单元规划：记忆与上下文管理，待编写。
""",
    )

if __name__ == "__main__":
    write(
        "示例工程/README.md",
        r"""
## 运行入口

VS Code打开本目录，使用根目录共享.venv。终端A启动，终端B读取：

```powershell
& ..\..\..\.venv\Scripts\python.exe server.py --port 8770 --capacity 2
& ..\..\..\.venv\Scripts\python.exe client.py --output-units 8
```

两条命令分别在两个终端，服务仅监听127.0.0.1。标准库、不安装依赖，后端人工延迟，输出是片段而不是LLM token。header公开模拟会话不是认证。Ctrl+C停止自己启动的服务。

## 代码导航

- [backend.py](./backend.py)：可中断等待与模拟片段生成。
- [server.py](./server.py)：/generate SSE、/cancel、/health、/stats、参数边界、容量槽与失败记录。
- [client.py](./client.py)：事件解析、重定向拒绝、首段/间隔/完成计时、分位数。
- [benchmark.py](./benchmark.py)：有界闭环并发、预热、完整请求分母与吞吐。
- [scheduler.py](./scheduler.py)：静态/连续批轮次及KV页数模拟，无实际GPU内核。
- [quantization.py](./quantization.py)：对称INT4算术与四条阈值Case，不实现AWQ/GPTQ。
- [demo.py](./demo.py)：临时端口自动演练、三个并发批次与取消，保存新的report-demo-01.json。
- [test_serving.py](./tests/test_serving.py)：接口、边界、过载、取消/断开、后端故障、SSE和统计。
- [requirements.txt](./requirements.txt)：无需额外包，测试工具来自共享环境。

## 压测与验证

```powershell
& ..\..\..\.venv\Scripts\python.exe benchmark.py --requests 20 --concurrency 2 --output report-my-c2.json
& ..\..\..\.venv\Scripts\python.exe demo.py
& ..\..\..\.venv\Scripts\python.exe -m pytest tests -q
& ..\..\..\.venv\Scripts\python.exe -m ruff check .
& ..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

demo自行启动临时服务，不要求手动8770；report-demo-01.json必须未存在，已存在时拒绝覆盖。作者数据详见 [[../参考工程验证记录|验证记录]]，教材完整步骤见 [[../00 推理服务与性能工程学习地图|学习地图]]。

capacity限制后端生成，不是HTTP连接/线程总数；仅教学，不提供生产TLS/auth/限流。SSE契约只与本工程客户端一致，不声明兼容OpenAI或vLLM接口。真实模型量化、硬件内存实测与vLLM部署是后续选修。
""",
        "推理服务与性能示例工程代码导航",
    )

if __name__ == "__main__":
    print("已写入单元27六讲、地图与代码导航")
