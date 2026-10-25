---
title: 第 1 讲：发出一次安全的模型 API 请求
tags:
  - llm-api
  - http
  - security
updated: 2026-10-25
cssclasses: ["guide-page", "guide-lesson"]
---

# 第 1 讲：发出一次安全的模型 API 请求

> [!nav] 页面导航
> 首次主线 8/11 · [[01_学习指南/11_LLM_API与Prompt/00 LLM API 与 Prompt 学习地图#学习顺序|单元 11：LLM API 与 Prompt]] · [[01_学习指南/02_测试与实验复现/逐讲学习/01 写第一个 pytest 测试|上一讲]] · [[01_学习指南/11_LLM_API与Prompt/逐讲学习/02 写清指令与组织上下文|下一讲]]

## 这一讲解决什么问题

Python 程序怎样把一段问题发给远程语言模型，又怎样拿到回答？我们先拆开一次 API 请求的组成，不马上依赖 SDK，也不需要真实密钥。

API（应用程序编程接口）可以理解为双方约定的“请求格式和回应格式”。HTTP 是常见网络传输协议：客户端发一个带地址、方法、header 和正文的请求，服务端返回状态码、header 和正文。JSON 是正文常用的数据表示格式，可以表达字符串、数字、布尔值、列表和字典。

## 最小请求

一个 Responses 风格的消息输入可以这样表示：

```python
payload = {
    "model": "some-model",
    "input": [
        {"role": "developer", "content": "请用一句话回答。"},
        {"role": "user", "content": "什么是 API？"},
    ],
}
```

`model` 选择服务端模型；`input` 保存消息列表；`role` 表示消息是谁发的；`content` 是消息文本。服务商也许支持 system/developer 等不同角色，或要求不同字段。不要把这个结构误认为所有平台的通用格式。

HTTP 请求还会有 `Content-Type: application/json`，告诉服务端正文是 JSON；`Authorization: Bearer ...` 通常用于证明调用者有权限。密钥是秘密凭证，不能贴进教程、源码、截图、日志或 Git。服务端响应通常有状态码，如 200 表示成功、400 表示请求格式/参数有问题、429 表示暂时超过速率限制；具体含义以服务商文档为准。

## 运行本单元的本机模拟请求

在 VS Code 打开 `示例工程/api_client.py`，然后从 `示例工程` 目录运行：

```powershell
..\..\..\.venv\Scripts\python.exe demo.py
```

这里的 `demo-key-no-charge` 是无权限的教学占位字符串，只发给绑定在 `127.0.0.1` 的本机假服务，不是真实 API key。代码会在随机本机端口启动服务，组装 JSON 请求，用 `urllib.request` 发送 POST，再读取 JSON 响应。退出 `with run_fake_provider()` 后，本地服务线程会关闭。

预期看到一条分类结果和使用量，再看到重复请求命中内存缓存。若系统安全软件阻止本机回环端口，先检查 Python 本机网络权限；不需要开启公网访问。

## 顺着代码读

`call_api` 首先验证 URL、密钥占位值、超时与尝试次数；然后用 `json.dumps` 将字典编码为 UTF-8 JSON。SHA-256 hash（哈希摘要）把 endpoint 与请求正文变成固定长度标识，用作幂等 header 和可选缓存键。哈希不是加密，不能用它隐藏请求正文。

`Request` 设置 URL `/v1/responses`、POST 方法和请求 header。`urlopen(..., timeout=...)` 最长等待给定秒数。成功响应读取后转成 Python 字典。`extract_output_text` 遍历所有 output item，只拼接 assistant message 的 `output_text`，因为真实响应也可能包含 reasoning、tool call 或其他内容。

当前 Python 工程用标准库只为了让 HTTP 和错误流程看得见；若转成真实模型调用，官方 SDK 通常会处理服务对象与响应类型等细节。OpenAI 官方示例使用 `client.responses.create(...)`，并从 SDK convenience property `response.output_text` 取聚合文本；它不等同于原始 HTTP JSON 必然有同名字段。[官方 API quickstart](https://platform.openai.com/docs/quickstart/make-your-first-api-request)

## 动手操作

1. 在 `demo.py` 中把 `ticket_text` 改为 `电脑无法登录，页面报错。`，运行脚本。预期假服务返回格式正确的 JSON，但固定示例服务的分类逻辑可能仍按简单规则返回 other；这说明模拟服务不是模型。
2. 在 `demo.py` 第一次 `call_api(...)` 调用中，把第三个参数 `"demo-key-no-charge"` 临时改成 `""`。预期抛出 `ValueError`，请求尚未发出；核对后恢复原占位值。
3. 在同一次调用中加入关键字参数 `timeout_seconds=0`，预期校验失败并提示必须大于 0。核对后删去这个临时参数，恢复演示。
4. 阅读 `api_client.py` 构造请求的地方，用文字指出授权 header 的字段名与用途；不打印字段值。错误记录应能帮助排错，同时避免暴露密钥。

## 常见错误

- **401/403：** 检查密钥、组织/项目权限和环境变量来源；不能把密钥打印到终端日志。
- **400：** 核对模型名、字段类型、消息内容和服务商 API 版本。
- **429：** 暂时超限或额度问题，先确认响应和速率限制规则；不能无上限快速重发。
- **请求成功但取不到文字：** 检查响应是否是拒答、工具调用、不完整状态或其他输出 item，不要假设 `output[0]` 一定是文本。
- **慢请求：** 设置合理 timeout，并区分一次请求超时与服务端是否实际处理完成。

## 练习

**跟做：** 在当前问题之前加入一组过去的 user 问题与 assistant 回答，解释 `input` 顺序。完成标准：消息仍是有序列表，依次为 developer 指令、过去的 user 问题、对应的 assistant 回答、当前 user 问题；不要把过去的回答接在当前问题后面。

**独立：** 用自己的话指出模型名、消息、授权 header、timeout、response usage 分别解决什么问题。

**迁移：** 选一种真实 API，阅读官方 quickstart 并整理它的请求 URL、Python SDK 调用、输出提取字段、密钥环境变量名。此练习先做文档调查，不运行付费请求。

> [!example]- 参考答案与解析
> 对话历史通常按时间从早到晚放入输入；若 assistant 回答是模型需要参考的历史，它在新 user 提问之前。每个平台对接续方式和是否需要显式携带历史有不同规定。
>
> model 选模型；input 传上下文/任务；Authorization 证明调用权限；timeout 限制单次等待；usage 帮助统计 token 使用量。usage 字段与 token 计数方式要按 API 响应文档解释。
>
> 迁移调查表至少记录接口版本、SDK 包名/版本限制、response item 结构、结构化输出支持模型范围，以及错误/限流处理方式。

## 先掌握与稍后再学

现在要掌握 HTTP 请求/响应、JSON 字段、超时和密钥不泄漏。流式响应、图片/音频输入、异步并发与 SDK 类型细节后续再学。

## 继续学习

> [!next] 下一步
> [[01_学习指南/11_LLM_API与Prompt/逐讲学习/02 写清指令与组织上下文|首次主线下一步：写清指令与组织上下文]]

> [!info]- 练习与记录
> [[01_学习指南/11_LLM_API与Prompt/示例工程/README#代码导航|查看源码]] · [[01_学习指南/11_LLM_API与Prompt/示例工程/README#运行|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 11：LLM API、Prompt 与结构化输出|本单元完成清单]]
> 按单元查阅时：[[01_学习指南/11_LLM_API与Prompt/逐讲学习/02 写清指令与组织上下文|单元内下一讲]]
> [[00_学习路线/01 从零开始建立共同基础|回看首次学习阶段]]
