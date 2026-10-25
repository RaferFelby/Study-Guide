---
title: Python 工程化参考工程
aliases:
  - ticketkit 示例工程
tags:
  - python
  - example-project
  - engineering
status: verified
updated: 2026-10-25
cssclasses: ["code-readme", "guide-page", "guide-code"]
---

# Python 工程化参考工程

> [!nav] 页面导航
> [[01_学习指南/01_Python工程化/00 Python 工程化学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/01_Python工程化/逐讲学习/01 运行Python并统计工单|从第一讲开始：运行Python并统计工单]]


配套教程：[[01_学习指南/01_Python工程化/00 Python 工程化学习地图|单元 01 学习地图]]；从[[01_学习指南/01_Python工程化/逐讲学习/01 运行Python并统计工单|第 1 讲：运行Python并统计工单]]开始。这是标准库教学工程，模拟工单与工具，不连接真实业务系统。文档在 Obsidian 中阅读；下列源码与配置链接交给 VS Code 打开。

## 安装与运行

工程声明需要 Python 3.11+，本机实际版本见作者验证记录。先确认终端位于本目录，并检查已有共享环境：

```powershell
..\..\..\.venv\Scripts\python.exe --version
..\..\..\.venv\Scripts\python.exe -m pip show learning-ticketkit
```

`pip show` 读取安装信息；找到包时检查可编辑源码位置是否为本工程。若提示包不存在，说明拟安装的是本地 `learning-ticketkit` 0.1.0、用途为导入当前教学源码、位置为根 `.venv`，获批后才执行下面一条安装命令。项目无第三方运行依赖；`--no-build-isolation` 要求共享环境已具备 pyproject.toml 声明的构建工具，缺少时另按根依赖规则处理，不自动升级。

```powershell
..\..\..\.venv\Scripts\python.exe -m pip install --no-build-isolation -e .
```

已有正确安装时，直接运行以下检查与示例：

```powershell
..\..\..\.venv\Scripts\python.exe -m unittest discover -s tests -v
..\..\..\.venv\Scripts\python.exe -m mypy --strict src
..\..\..\.venv\Scripts\python.exe -m ticketkit
..\..\..\.venv\Scripts\python.exe -m ticketkit.benchmark
```

本地源码可编辑安装在构建工具齐备时通常不需要下载；缺少构建工具时需先确认补装方案。示例运行无需 GPU 或网络。上述相对解释器路径要求终端位于本目录；从其他目录运行时，改用仓库根目录共享环境的绝对解释器路径。默认日志写入当前工作目录的 `logs/`。只运行第 1 讲独立的小脚本时无需安装本包。

默认预期业务输出：

```text
{"open": 50000, "closed": 50000}
["fast:ok", "slow:timeout"]
```

时间、日志时间戳与内存数值会因环境不同而变化。控制台日志写 stderr，业务输出写 stdout。测试会故意触发重试、超时和错误，不应把预期测试日志误认为测试失败，最终看 unittest 总结和退出码。

## 代码导航（VS Code）

1. [data.py](./src/ticketkit/data.py)：数据类、边界校验、惰性生成与统计。
2. [config.py](./src/ticketkit/config.py)：环境配置、错误链与敏感字段表示。
3. [resilience.py](./src/ticketkit/resilience.py)：`ParamSpec`、装饰器、有限重试与上下文管理器。
4. [observability.py](./src/ticketkit/observability.py)：`ContextVar`、请求上下文、控制台与轮转日志。
5. [async_tools.py](./src/ticketkit/async_tools.py)：模拟 IO、并发限制、超时和取消。
6. [__main__.py](./src/ticketkit/__main__.py)：组件装配；[benchmark.py](./src/ticketkit/benchmark.py)：Python 分配峰值测量。
7. [test_engineering.py](./tests/test_engineering.py)：行为验证与故障注入。
8. [pyproject.toml](./pyproject.toml)：包元数据与静态检查配置；[requirements-dev.txt](./requirements-dev.txt)：开发依赖锁定。

补充课独立脚本：[object_copy_demo.py](./object_copy_demo.py) 演示引用、浅／深复制和保留输入的工单函数；[test_object_copy.py](./tests/test_object_copy.py) 检查对象关系、切片、非法输入与 frozen 边界。在本目录运行 `..\..\..\.venv\Scripts\python.exe object_copy_demo.py`，无需可编辑安装。教学正文见 [[01_学习指南/01_Python工程化/逐讲学习/04 分清对象引用与浅深复制|引用与复制]]。

## 验证范围与限制

- strict 检查覆盖 `src/`，测试使用标准库 unittest。
- 内存实验比较 Python 跟踪的分配峰值，不报告 RSS/GPU 内存。
- 同步 retry 不适用于 async 函数；不带跨调用总预算或随机抖动。
- wait_for 是协作式超时，无法强制中止阻塞线程或撤销远端操作。
- logger 在单进程启动时配置，多进程集中日志是后续学习内容。
- API token 不参与真实请求；repr 隐藏不是加密，也不防止主动打印。

所有学习者改动应能通过相应回归测试，并在报告中写明新增行为和限制。
