---
title: 单元 04 示例工程：数据结构与算法工具箱
tags:
  - example
  - algorithms
  - unittest
status: published
updated: 2026-10-25
cssclasses: ["guide-page", "guide-code"]
---

# 单元 04 示例工程：数据结构与算法工具箱

> [!nav] 页面导航
> [[01_学习指南/04_数据结构与算法/00 数据结构算法学习地图#学习顺序|返回本单元课表]] · [[01_学习指南/04_数据结构与算法/逐讲学习/01 从复杂度到数组与哈希表|从第一讲开始：从复杂度到数组与哈希表]]

这是单元 04 的最小可运行工程。基础源码从 app/algorithms.py 开始，分讲练习及 tests 目录见下方代码导航。代码使用 Python 标准库，不需要安装第三方依赖。

## 在 VS Code 中运行

在本目录打开终端，执行：

~~~powershell
..\..\..\.venv\Scripts\python.exe -m unittest discover -s tests -v
~~~

命令使用 Python 内置测试模块。unittest 运行测试，discover 自动发现测试；-s tests 指定从 tests 目录搜索。预期所有测试通过。不同 Python 版本的耗时和测试排列顺序可能略有差异。

## 代码导航

- [app/algorithms.py](./app/algorithms.py)：数组、哈希表、链表、堆、树、图、窗口、回溯、动态规划、LRU 和拓扑排序。
- [app/graph_practice.py](./app/graph_practice.py)：第 3 讲前序与深度、DFS/BFS 可达性和带输入校验的工作流顺序。
- [app/dynamic_programming.py](./app/dynamic_programming.py)：第 5 讲括号、两版楼梯计数、小规模组合枚举与二维预算表。
- [tests/test_algorithms.py](./tests/test_algorithms.py)：正常输入、空输入、重复值、循环图和缓存边界测试。
- [tests/test_practice.py](./tests/test_practice.py)：新增练习的边界、失败路径及小规模穷举对照。

- [window_practice.py](./app/window_practice.py)：有序数组原地去重、正整数最短和窗口、按秒记录的最忙日志窗口。
- [test_windows.py](./tests/test_windows.py)：空输入、正数约束、时间端点、并列处理及小规模穷举对照。

第 4 讲的完整 `lesson_04.py` 由学习者按 [[01_学习指南/04_数据结构与算法/逐讲学习/04 二分双指针与滑动窗口|正文]]创建。日志约定 `(结束时点-60, 结束时点]`，返回索引 `[start,stop)`；跨天输入用连续秒数，时间戳必须非降序。

## 练习方式

1. 先只看测试名称，猜每个函数的输入输出。
2. 再看函数实现，用纸写出一个小输入的变量变化。
3. 修改一个边界测试，先让它失败，再修复实现。
4. 在单元 04 的练习记录中保存思路、复杂度、错误和复盘结果。

## 设计边界

graph_practice 的可达性接口要求所有节点，包括每个邻居，都列为字典键；缺少起终点返回 False。既有 shortest_steps 的较宽松契约保持原样，不存在的起点按没有后继处理，起终相同返回 0。两者不是完全相同的接口。

预算函数按非负整数输入，只用于独立、每项最多一次、收益可相加的工具。枚举适合少数工具，二维表还受整数预算大小限制；它不是具有依赖、失败重试、实际质量反馈的执行调度器。树递归只用于小规模无环普通树。

工程中的函数用于学习和测试，不是生产级通用算法库。返回顺序只在函数契约规定时保证；并列结果可能有多种合法顺序。真实项目应优先使用标准库和成熟实现，并为输入规模、错误处理和性能建立自己的契约。
