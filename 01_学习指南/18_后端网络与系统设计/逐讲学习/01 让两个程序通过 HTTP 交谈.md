---
title: 第 1 讲：让两个程序通过 HTTP 交谈
tags: [lesson, http, json]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 1 讲：让两个程序通过 HTTP 交谈

> [!nav] 页面导航
> [[01_学习指南/18_后端网络与系统设计/00 后端网络与系统设计学习地图#学习顺序|单元 18：后端网络与系统设计]] · [[01_学习指南/18_后端网络与系统设计/逐讲学习/02 校验接口参数并隔离用户|下一讲]]

## 本讲任务与前置

之前运行一个Python脚本，它直接调用函数。现在浏览器、手机或另一个程序想调用同一业务，需要约定消息格式。我们先让两个本机程序通过HTTP交谈，得到一条虚构退款政策。复习字典/JSON和`main()`入口；不了解端口和服务器的同学从下一段开始。

## 概念与直觉

客户端是主动发请求的程序；服务端是持续等待并处理请求的程序。HTTP是一套请求和响应规则，并不限定用Python。JSON是正文的一种文本格式，HTTP头说明这份正文是什么、怎样解释。

URL `http://127.0.0.1:8765/query`中：`http`是通信协议；`127.0.0.1`是本机回环地址；8765是端口，操作系统用它把消息交给监听程序；`/query`是路径，服务按路径选择动作。邮局类比有助于理解分发，但实际是网络套接字收发字节，没有邮件箱对象。

请求含方法、路径、头、正文。GET在本示例读取状态，POST提交带正文的操作。响应含状态码、头、正文。REST是一类以资源和标准HTTP语义组织接口的设计方式；不是JSON的别名，也不要求所有操作都叫POST。我们用`/jobs/{id}`代表一个任务资源。

## 最小示例：认识将要发送的正文

在示例工程新建`lesson_json.py`，输入并保存：

```python
import json

body = {"question": "refund"}
text = json.dumps(body)
payload = text.encode("utf-8")
print(text)
print(len(payload))
print(json.loads(payload.decode("utf-8"))["question"])
```

`dumps`把字典变成JSON字符串；`encode`变成网络发送的字节；`len(payload)`计算字节数，服务响应的Content-Length也是字节数。`decode`还原字符串，`loads`解析成字典。不要把字符数当字节数，中文UTF-8常占多个字节。

运行：

```powershell
..\..\..\.venv\Scripts\python.exe lesson_json.py
```

预期依次为`{"question": "refund"}`、22、`refund`。空格来自默认JSON序列化，不影响字段含义。

## 动手一：先跑自动演示

在VS Code“文件→打开文件夹”选择本单元`示例工程`，终端工作目录应以`18_后端网络与系统设计\示例工程`结尾。运行：

```powershell
..\..\..\.venv\Scripts\python.exe demo.py
```

demo创建本次专用临时目录和数据库，启动本机服务与工作线程，再用客户端请求，最后关闭服务并清理本次临时文件。首先找`health (200, ...)`；随后三条query为Alice首次未命中、再次命中、Bob首次未命中。`request_id`和端口每次变化是正常的，不要照抄它们作固定答案。

## 动手二：两个终端手动运行

在终端A：

```powershell
..\..\..\.venv\Scripts\python.exe server.py --port 8765
```

`--port`指定监听端口；服务出现地址并持续等待是成功，不是卡死。它默认把任务存在示例工程`jobs.sqlite`，以后重启仍读取此文件。不要为“重新开始”直接删除数据库。

在VS Code终端栏点“+”新建终端B，同样位于示例工程，执行：

```powershell
..\..\..\.venv\Scripts\python.exe client.py
```

客户端依次GET健康检查、两次POST查询、POST任务。它使用`urllib.request.Request`组装消息，`timeout=3`限制套接字等待；HTTPError是收到非成功状态时的异常，代码仍读取该响应JSON。禁用代理仅用于本机演示，避免环境代理把回环请求转发出去。

预期query返回`answer: 退款期限为30天。`。浏览器可打开`http://127.0.0.1:8765/health`查看JSON；直接打开`/query`发送的是GET，并不等价于POST。学习结束在终端A按Ctrl+C停止服务。

## 源码阅读顺序与执行过程

从[[01_学习指南/18_后端网络与系统设计/示例工程/README|代码导航]]打开`client.py`的request，再看`server.py`的do_POST/handle_api。继承只在HTTP适配处出现：BaseHTTPRequestHandler已经处理请求行/头的读取，我们提供do_GET/do_POST。暂不需要手写协议解析器。

服务的路径判断把请求交给QueryService.query；业务函数只认识owner和question，不认识HTTP头。reply将业务结果编码成JSON字节，先发送状态和头，再发送正文。Content-Type让客户端知道这是JSON；Content-Length声明字节长度；X-Request-ID关联本次请求。协议层不会自动理解“退款”，业务字典才给出合成答案。

## 常见错误与排查

- ConnectionRefusedError：确认终端A仍运行、两个程序使用同一端口、URL写127.0.0.1。服务未启动时反复运行客户端不能解决。
- WinError10048/地址占用：已有程序监听8765。先确认是否就是你此前启动的服务，关闭自己的旧服务；或改为8766并同步client.py中的base_url。
- 一直不出现下一条命令提示：server在等待请求，正常；输入客户端命令应另开终端。
- 乱码：文件保存UTF-8；PowerShell显示有问题时可先设置`$env:PYTHONIOENCODING='utf-8'`再运行。
- 系统防火墙/运行沙箱阻止socket：记录实际错误；本单元只需回环连接，不应为了学习开放公网端口。作者环境的沙箱差异见验证记录。

## 练习与答案

跟做：保留health与一条query输出，标出方法、路径、状态码、正文。完成判断是四项都能在代码或输出中对应。

独立：不运行服务，画出client.request到retrieve再返回JSON的顺序。提示：网络字节转换发生在两端，不发生在POLICIES字典中。

迁移：如果以后把检索换成GPU模型推理，哪些层应保持接口？完成判断：列出业务层内部可更换部分和客户端仍需的契约。

> [!example]- 参考答案与解析
> 请求POST /query，正文question=refund；响应200与answer。顺序为字典→JSON字节→HTTP→路径/字段检查→query→retrieve→结果字典→HTTP JSON→客户端解析。
>
> GPU推理可替换业务层retrieve，HTTP契约中的question和answer可继续使用；模型加载、设备和推理队列属于服务内部资源。若延迟大幅增加，客户端需要转为任务提交/轮询，不能只换函数后假定超时行为不变。

## 本讲完成后

你应能启动、请求、停止一个本机服务，并解释“消息格式”和“业务计算”分别在哪层。下一讲处理错误输入和用户权限。协议参考：[HTTP语义RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html)；标准库服务仅用于学习，部署限制见[Python http.server文档](https://docs.python.org/3.13/library/http.server.html)。

> [!nav] 路线续读
> 若本讲已到当前路线列出的范围末尾，返回原阶段继续下一项或检查产物；继续单元学习时沿下方“下一讲”。
>
> - [[00_学习路线/05 学习推理系统与GPU工程#机制入门：先做本地流式服务|学习推理系统与GPU工程 · 机制入门：先做本地流式服务]]

## 继续学习

> [!next] 下一步
> [[01_学习指南/18_后端网络与系统设计/逐讲学习/02 校验接口参数并隔离用户|下一讲：校验接口参数并隔离用户]]

> [!info]- 练习与记录
> [[01_学习指南/18_后端网络与系统设计/示例工程/README#代码导航|查看源码]] · [[01_学习指南/18_后端网络与系统设计/示例工程/README#运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 18：后端、网络与系统设计|本单元完成清单]]
