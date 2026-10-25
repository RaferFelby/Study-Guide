---
title: 单元 12 参考工程验证记录
tags:
  - validation
  - rag
  - data-engineering
updated: 2026-10-04
status: verified
cssclasses: ["guide-page", "guide-reference"]
---

# 单元 12 参考工程验证记录

> [[01_学习指南/12_RAG数据工程/00 RAG 数据工程学习地图|单元 12：RAG 数据工程]] · [[02_学习记录/00 我的学习记录|学习者自己的记录]] · [[90_参考与维护/课程覆盖/13 RAG 数据工程（P0）#模块 13：RAG 数据工程（P0）|K/C 覆盖映射]]

## 验证范围

作者侧验证仅说明本地离线教学工程通过了列出的检查，不代表学习者已经完成 C13 验收，也不代表生产级 RAG 或真实向量语义检索已验证。

| 项目 | 本次结果 |
|---|---|
| Python | 3.13.12 |
| 关键依赖 | 本单元源码仅使用标准库；pytest 8.4.2、ruff 0.16.9 使用共享 `.venv` 中已有工具，无依赖安装 |
| 数据库 | SQLite 3.50.4；demo 使用临时目录，测试使用内存 SQLite |
| 设备 | CPU；没有神经网络或 GPU 运算 |
| 来源解析 | Markdown、HTML、CSV fixtures；不含 PDF parser/OCR |
| 检索 | 词面重叠教学探针；fixed 10 chunks、structure 8 chunks；两策略三条标注 query 均命中 Recall@3=3/3，不代表真实语义检索效果 |
| 测试/质量检查 | pytest：14 passed；ruff check：All checks passed；pip check：No broken requirements found；demo 正常完成 |

## 已验证与未验证

- 计划验证：解析时来源定位、HTML 元素过滤、CSV 行列保留、切块边界、未变化跳过、版本替换、权限过滤、删除后索引一致性。
- 未验证：真实 PDF 解析、扫描件 OCR、真实 sentence embedding、向量数据库、模型质量/召回率、生产 ACL、跨服务事务与索引对账。
- 测试结论仅覆盖固定小 fixture 和函数行为；严肃召回对照需要更大的带标注问题集。
