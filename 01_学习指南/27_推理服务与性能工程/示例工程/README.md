---
title: 推理服务与性能示例工程代码导航
tags: [learning, serving, performance]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# 推理服务与性能示例工程代码导航

> [!nav] 页面导航
> [[01_学习指南/27_推理服务与性能工程/00 推理服务与性能工程学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/27_推理服务与性能工程/逐讲学习/01 让客户端逐段收到推理输出|从第一讲开始：让客户端逐段收到推理输出]]

## 运行入口

第 1～4 讲的流式服务入门只需首次 Python／请求基础与单元 18 第 1 讲的 HTTP；后端为本工程的合成片段，不要求先完成 SFT、Agent 或交付单元。第 5～6 讲另补注意力、缓存和参数精度的前置，具体范围见本单元地图。

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

demo自行启动临时服务，不要求手动8770；report-demo-01.json必须未存在，已存在时拒绝覆盖。作者数据详见 [[90_参考与维护/单元验证/27 推理服务与性能工程验证记录|验证记录]]，教材完整步骤见 [[01_学习指南/27_推理服务与性能工程/00 推理服务与性能工程学习地图|学习地图]]。

capacity限制后端生成，不是HTTP连接/线程总数；仅教学，不提供生产TLS/auth/限流。SSE契约只与本工程客户端一致，不声明兼容OpenAI或vLLM接口。真实模型量化、硬件内存实测与vLLM部署是后续选修。
