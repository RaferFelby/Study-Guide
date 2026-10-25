---
title: 单元 17 示例工程导航
tags: [code, sql, integration]
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# 单元 17 示例工程

> [!nav] 页面导航
> [[01_学习指南/17_SQL数据库与数据集成/00 SQL 数据库与数据集成学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/17_SQL数据库与数据集成/逐讲学习/01 建立关系表并查询工单|从第一讲开始：建立关系表并查询工单]]

标准库SQLite工单数据：用户/产品/工单/事件、12个固定业务查询、参数绑定/租户只读/行数和VM预算、CSV/API夹具增量导入、备份恢复。所有数据库位于本次工程内唯一临时目录，退出自动清理，不覆盖已有文件。

## 运行

在本目录VS Code PowerShell终端：

```powershell
..\..\..\.venv\Scripts\python.exe demo.py
..\..\..\.venv\Scripts\python.exe -m pytest -q tests
..\..\..\.venv\Scripts\python.exe -m ruff check .
..\..\..\.venv\Scripts\python.exe -m ruff format --check .
```

预期首次插入7、重复跳过7；alpha6工单、open3、NULL金额1、已知平均2000分；JOIN事件3行/2不同工单；计划使用复合索引；API夹具新增1更新1；恢复8工单。金额/数据虚构。

## 代码导航

- [schema.sql](./schema.sql)：v1关系表、复合外键/唯一/检查约束和索引。
- [database.py](./database.py)：启用外键、初始化、拒绝覆盖的备份/恢复。
- [importing.py](./importing.py)：CSV/API映射、UTC/整数字段、来源摘要、版本与事务导入。
- [queries.py](./queries.py)：12个业务问题及SQL模板，含JOIN/NULL/CTE/窗口/分页。
- [readonly.py](./readonly.py)：mode=ro、query_only、authorizer、可信tenant、参数/限行/VM预算。
- [demo.py](./demo.py)：完整流程、重复统计反例、计划和恢复。
- [tickets.csv](./fixtures/tickets.csv) · [api_update.json](./fixtures/api_update.json)：固定合成来源，无真实请求。
- [test_database.py](./tests/test_database.py)：导入/回滚、关系边界、查询/权限、计划和恢复内容对照。
- [requirements.txt](./requirements.txt)：仅标准库，SQLite3.25+窗口函数；共享环境已满足。

## 限制

SQLite无服务器账户，此原型以只读连接/模板限制实现受限查询；context无真实认证。未支持任意生成SQL、连接池、后续迁移链、API网络分页/删除/并发同步。VM回调不是硬总时限。导入先查后写只验证单连接事务，非分布式幂等。临时备份不持久，生产需权限/保留期/异地存储。

[[01_学习指南/17_SQL数据库与数据集成/00 SQL 数据库与数据集成学习地图|单元 17：SQL 数据库与数据集成]]。
