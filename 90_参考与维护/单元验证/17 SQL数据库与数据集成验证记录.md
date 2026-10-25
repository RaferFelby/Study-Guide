---
title: 单元 17 参考工程验证记录
tags: [validation, sql, author-record]
updated: 2026-10-11
cssclasses: ["guide-page", "guide-reference"]
---

# 单元 17 参考工程验证记录

> [!nav] 页面导航
> [[01_学习指南/17_SQL数据库与数据集成/00 SQL 数据库与数据集成学习地图|学习地图]] · [[01_学习指南/17_SQL数据库与数据集成/示例工程/README|代码导航]]

## 环境与执行

Windows共享Python3.13.12，SQLite3.50.4，pytest8.4.2，Ruff0.16.9；没有安装新依赖。2026-10-11在示例工程运行完整demo和测试。

- 14个测试通过（0.71秒），Ruff规则检查通过；SQL模板已整理为多行便于阅读。
- 首次导入7，重复导入跳过7；alpha租户6工单，open/resolved各3，Carol无工单，Analytics产品计数0。
- 已知金额5笔，平均2000分；NULL金额1笔；事件JOIN得到3行，但不同工单为2。
- 窗口查询每用户最新为T005/T006；高于平均金额为T004/T006；参数绑定的恶意status不改变查询结构。
- EXPLAIN QUERY PLAN输出使用idx_tickets_tenant_status_created复合索引。
- API夹具新增1更新1；备份恢复后8工单，测试对照全部业务行并检查完整性。
- 已覆盖较低版本跳过、同版本不同内容拒绝并回滚、跨租户外键拒绝、行数限制、VM预算、写入/ATTACH拒绝及恢复文件不覆盖。

## 边界

作者运行结果不表示学习者已掌握，学习记录保持未勾选。数据全为合成；SQLite无服务器账户，未验证PostgreSQL角色、真实网络API或并发导入。只读工具采用固定SQL模板，未接受模型任意SQL。VM预算约束执行回调，不能承诺端到端硬时限。备份demo使用临时目录，未建立生产备份策略。未逐页打开Obsidian检查视觉排版。
