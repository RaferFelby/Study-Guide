---
title: AI Agent 算法学习教程
tags: [index, repository]
updated: 2026-10-26
cssclasses: ["guide-page", "guide-code"]
---

# AI Agent 算法学习教程

> [!nav] 页面导航
> [[00 从这里开始|打开学习首页]]，先完成当前小目标，再沿单元导航继续。教材默认在 Obsidian 阅读，代码在 VS Code 操作。

## 常用入口

在 GitHub 上可从 [学习首页](./00%20从这里开始.md) 或 [首次学习主线](./00_学习路线/01%20从零开始建立共同基础.md) 查看内容。教材中的 `[[双链]]` 和 callout 按 Obsidian 组织；要顺着完整导航学习，请克隆或下载本仓库，在 Obsidian 中将仓库文件夹作为知识库打开，再进入 `00 从这里开始.md`。配套源码用 VS Code 打开。

仓库提供教材、示例源码、练习数据、依赖清单和阅读样式。Python 虚拟环境、缓存、运行结果和本机窗口状态不随仓库上传；运行示例前按下方共享环境说明准备环境。

- [[00_学习路线/01 从零开始建立共同基础|先走 11 讲首次学习主线]]
- [[90_参考与维护/01 使用与环境/01 共享Python环境与运行约定|共享 Python 环境、依赖与运行约定]]
- [[90_参考与维护/00 参考与维护导航|参考、覆盖与维护]]

本机示例共用根目录 `.venv`，安装或变更依赖遵守 [[AGENTS|工作区协作约定]]。

## 代码导航

- [sync_learning_overview.py](./scripts/sync_learning_overview.py)：从完成清单同步学习总表，保留手填安排。
- [test_sync_learning_overview.py](./scripts/test_sync_learning_overview.py)：核对进度计数、资料缺失与个人字段保留。
- [guide_structure.json](./scripts/guide_structure.json)：单元、首次主线与总表入口的结构记录。
- [ai-learning.css](./.obsidian/snippets/ai-learning.css)：首页、路线、地图、正文、表格和代码区的统一阅读样式。
