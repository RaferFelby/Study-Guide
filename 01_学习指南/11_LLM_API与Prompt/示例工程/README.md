---
title: 单元 11 示例工程导航
tags:
  - code
  - llm-api
  - prompt
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# 单元 11 示例工程

> [!nav] 页面导航
> [[01_学习指南/11_LLM_API与Prompt/00 LLM API 与 Prompt 学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/11_LLM_API与Prompt/逐讲学习/01 发出一次安全的模型 API 请求|从第一讲开始：发出一次安全的模型 API 请求]]

本工程用 Python 标准库向本机 HTTP 假服务发送 Responses 风格请求，再解析和校验结构化输出、演示限流重试与缓存，并比较三版固定评估夹具。它不调用真实模型、不访问外网、不需要 API key，也不产生模型费用。固定输出仅用来测试程序流程，不能说明模型效果。

## 运行

在 VS Code 打开本目录，在该目录的 PowerShell 终端运行：

```powershell
..\..\..\.venv\Scripts\python.exe demo.py
..\..\..\.venv\Scripts\python.exe -m pytest -q
```

第一条运行端到端演示；第二条用共享 `.venv` 的 pytest 执行 `tests/test_*.py`。预期会看到 JSON 分类结果、缓存命中、429 模拟重试次数及三版 Prompt 的格式率/任务率/token/示例成本。

## 代码导航

- [api_client.py](./api_client.py)：HTTP 请求、timeout、临时错误重试、稳定请求 key、可选内存缓存、响应文本提取。
- [fake_provider.py](./fake_provider.py)：只监听本机回环地址的假服务；产生成功、429、400 的固定响应。
- [structured_output.py](./structured_output.py)：JSON 解析、课程 Schema 子集验证和业务语义验证。
- [evaluation.py](./evaluation.py)：固定 case ID 的三个 Prompt 版本对照与指标汇总。
- [demo.py](./demo.py)：启动本地服务、发送请求、校验输出、展示有限重试和评估夹具。
- [test_api_client.py](./tests/test_api_client.py)：请求成功、429 重试、有上限、400 不重试、缓存作用域和配置失败。
- [test_structured_output.py](./tests/test_structured_output.py)：JSON 语法、字段/类型、证据和类别语义检查。
- [test_evaluation.py](./tests/test_evaluation.py)：指标、参数边界和固定评估集一致性。
- [requirements.txt](./requirements.txt)：本单元最小依赖说明。

## 真实服务边界

假服务响应参考 Responses API 的消息输出形态，但只实现教材用到的少量字段。真实服务可能有不同的 SDK、model 名、schema 能力、错误响应、幂等保证、限流和计费规则。真实调用前要查该服务当前文档、确认成本和数据权限；不要把本机假服务的密钥占位值、单价、模型结果或 idempotency 行为当作生产依据。
