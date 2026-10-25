---
title: MCP与工具生态参考工程验证记录
tags: [validation, mcp, stdio]
updated: 2026-10-12
cssclasses: ["guide-page", "guide-reference"]
---

# MCP与工具生态参考工程验证记录

## 入口、版本与环境

[[01_学习指南/30_MCP与工具生态/00 MCP与工具生态学习地图|学习地图]] · [[01_学习指南/30_MCP与工具生态/示例工程/README|代码导航]]。本页记录作者实际运行，不代表学习者已完成，也不代表完整协议符合性认证。

2026-10-12，在 Windows、工作区根共享 Python 3.13.12、pytest 8.4.2、Ruff 0.16.9 中执行。实际检查共享环境未安装 mcp 包；本工程按教学需要使用标准库实现固定消息子集，运行不需要该包，无依赖安装或环境变更。

规范采用核对过的 [2026-07-28 基础协议](https://modelcontextprotocol.io/specification/2026-07-28/basic/index)、[版本规则](https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning)、[发现](https://modelcontextprotocol.io/specification/2026-07-28/server/discover)和 [stdio 传输](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio)。新版本每请求携带元数据，不使用旧版 initialize 握手；本实现明确不自动回退旧版。

## 实际本地通信结果

运行 `demo.py --output report-author-20261012.json`，报告在示例工程中生成，未覆盖旧文件。客户端实际启动本工程 Python 子进程，通过 stdin/stdout 传 UTF-8 JSON；不只是直接调用服务分派函数。

| 项目 | 实际结果 | 解释 |
| --- | --- | --- |
| discover | supportedVersions 为 2026-07-28，三类能力 | 自报信息，不是身份认证 |
| reader 工具清单 | get_policy、get_support_note | 受信演示启动范围 |
| guest 工具清单 | get_policy | 隐藏内部能力并非唯一权限检查 |
| 正常工具 | isError=False，固定公开 URI、v1 | 合成退款资料，不是业务事实验证 |
| 资源读取 | knowledge://public/refund-v1 | 固定 URI 映射，没有任意文件/网络访问 |
| 提示获取 | user/text 消息 | 仅准备模板，没有模型调用 |
| 非法参数 | RemoteError，-32602 | 连接仍可用，后续 ping 成功 |
| guest 直接调用内部工具 | isError=True | 读取前拒绝，没有成功资料 |
| guest 内部资源读取 | 应用错误码 1001 | 本工程约定，不是统一协议权限码 |
| unavailable 工具 | isError=True | 合成故障，不是实际网络断连 |
| 三个自有服务进程 | 正常退出 | 输入关闭后回收，未结束其他进程 |

报告中 llm_called=False、external_application_connected=False。reader/guest 不是实际身份，启动配置不提供真实用户认证。

## 源码测试与错误路径

40 项测试实际通过，耗时 2.30 秒，无跳过。Ruff 规则检查通过，7 个 Python 文件完成格式检查。

覆盖每请求元数据、版本不支持及其支持列表、非法 ID、通知不回包、工具 Schema/结果、缺失/额外/错误类型参数、能力过滤与直接调用拒绝、clientInfo 伪装无效、任意 URI 拒绝、提示不执行工具、工具故障与资源错误、坏 JSON 后继续处理、超限流停止、真实中文 stdio、RPC 错误后连接恢复及关闭。

实际启动测试自己的临时假服务，分别制造 stdout 非 JSON 日志、错误 ID、同时 result/error、进程退出、超时和超长输出。客户端抛出本地错误并回收自己的服务；测试确认读取线程结束和管道关闭。权限测试替换资料读取函数为“调用就失败”，证明 guest 拒绝路径在读内部资料前停止。

## 教材与导航复核

六讲 6 个完整 Python 最小示例分别在本工程用共享解释器实际运行通过。全库 281 份正式文档的 YAML、标题层级、围栏、表格双链和本地链接检查发现 0 个问题，全部可从学习首页沿链接到达。未进行 Obsidian 界面视觉验收。作者检查不勾选学习者任务。

## 未做与实现边界

未用官方 SDK、外部宿主或 Inspector 做互操作验证，未实现完整 JSON Schema 2020-12、MRTR、订阅、任意通知路由、并发请求、分页/缓存、旧版回退、HTTP/OAuth、生产认证或写操作。只宣称本工程列出的消息与实际本地演练，不宣称兼容所有 MCP 客户端或符合完整规范。

stderr 日志实际发生，stdout 保持消息格式。测试只检查本工程与受控假服务；stdio 子进程没有自动获得操作系统沙箱。没有真实模型成功率、费用、远程部署、网页点击或 Obsidian 界面视觉验收。

最终源码再次运行 40 项测试，2.21 秒通过，无跳过；Ruff 规则与格式检查通过。临时假服务和教学脚本结束后清理，生成报告由 .gitignore 排除。

作者维护脚本 11 项测试另行通过，0.15 秒，包括新增教材生成器导入不写文件的检查；这与本单元 40 项示例测试分开记录。
