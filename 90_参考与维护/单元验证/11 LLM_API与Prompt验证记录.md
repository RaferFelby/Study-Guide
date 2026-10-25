---
title: 单元 11 参考工程验证记录
tags:
  - verification
  - llm-api
  - prompt
updated: 2026-10-04
status: verified
cssclasses: ["guide-page", "guide-reference"]
---

# 单元 11 参考工程验证记录

> [[01_学习指南/11_LLM_API与Prompt/00 LLM API 与 Prompt 学习地图|单元 11：LLM API 与 Prompt]] · [[01_学习指南/11_LLM_API与Prompt/示例工程/README|源码导航]]

## 验证范围

工程只在 localhost 运行一个 HTTP 假服务。验证 Python 标准库 HTTP POST、Responses 风格文本抽取、有限重试/缓存、JSON/结构/语义校验和 Prompt 评估指标计算。不访问真实 LLM API，不需要 API key，不产生模型费用。

## 环境和结果

- Python：3.13.12；pytest 8.4.2；Ruff 0.16.9。
- 依赖：工程代码只用 Python 标准库；pytest、ruff 使用共享 `.venv` 已装版本，本次未新增或升级依赖。
- 设备：CPU；本工程不调用 PyTorch/GPU。
- `python -m pip check`：通过，未发现依赖冲突。
- `python -m ruff check .`：通过；`python -m ruff format --check .`：通过。
- `python -m pytest -q`：30 passed。
- `python demo.py`：退出码 0；假服务返回 refund JSON，重复请求命中缓存，模拟限流后第 2 次成功；Prompt 夹具的 v1 格式率/任务率为 2/3，v2 为 1 和 2/3，v3 为 1 和 1。
- 当前工具捕获终端的中文文字显示乱码，token/请求逻辑由集成测试断言验证；预期在 UTF-8 终端阅读 demo 的中文提示。
- 限制：固定 JSON 输出和评估数据是测试夹具，不是模型生成结果；夹具的示例价格不是服务商报价。没有验证真实 API 的兼容性、真实模型效果、实际延迟、usage 或计费。

## 检查的不变量

- 请求超时、尝试次数和退避配置有边界；只重试约定中的暂时错误，400 不重试。
- 同一请求重试使用稳定 request key；成功缓存可选开启，缓存作用域区分凭证摘要。
- API 原始响应可能有非文本 output item，提取时只取 assistant output_text。
- JSON 结构校验与输入相关的语义校验分开进行。
- 三个 Prompt 版本使用同一组唯一 case ID，分别统计格式成功、任务标签正确、延迟、token 和估算成本。
- 错误路径可观测并有明确降级值；密钥不进入日志/异常信息。
