---
title: 第 6 讲：比较MCP与直接函数调用并完成验收
tags: [learning, mcp, protocol]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 6 讲：比较MCP与直接函数调用并完成验收

> [!nav] 页面导航
> [[01_学习指南/30_MCP与工具生态/00 MCP与工具生态学习地图#学习顺序|单元 30：MCP与工具生态]] · [[01_学习指南/30_MCP与工具生态/逐讲学习/05 验证权限拒绝超时与连接回收|上一讲]] · [[01_学习指南/30_MCP与工具生态/00 MCP与工具生态学习地图#完成后继续|学完继续]]

## 本讲要解决的问题与前置

学会连接后，还需决定什么时候值得使用 MCP。单个内部函数是不是一定要包装成服务？本讲对照直接调用与 MCP 返回的同一记录，再整理验收报告。

前置是五讲及 [[01_学习指南/11_LLM_API与Prompt/00 LLM API 与 Prompt 学习地图|模型 API 与结构化消息]]、[[01_学习指南/15_工具调用协议与工具设计/00 工具调用协议与工具设计学习地图|工具设计]]。当前不调用任何模型 API，不要求 API key。

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

[[90_参考与维护/单元验证/30 MCP与工具生态验证记录|作者实际结果和未测范围]] · [[01_学习指南/30_MCP与工具生态/示例工程/README|代码导航]]。下一单元：[[01_学习指南/31_推理与工具数据构造/00 推理与工具数据构造学习地图|推理与工具数据构造]]。

## 继续学习

> [!next] 下一步
> [[01_学习指南/30_MCP与工具生态/00 MCP与工具生态学习地图#完成后继续|本单元完成后继续]]

> [!info]- 练习与记录
> [[01_学习指南/30_MCP与工具生态/示例工程/README#代码导航|查看源码]] · [[01_学习指南/30_MCP与工具生态/示例工程/README#先运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 30：MCP与工具生态|本单元完成清单]]
