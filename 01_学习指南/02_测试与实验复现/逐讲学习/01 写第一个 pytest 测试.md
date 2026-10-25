---
title: 第 1 讲：写第一个 pytest 测试
aliases:
  - 测试与实验复现 01
  - pytest 入门
tags:
  - curriculum
  - python
  - testing
status: published
updated: 2026-10-25
cssclasses: ["learning-note", "guide-page", "guide-lesson"]
---

# 第 1 讲：写第一个 pytest 测试

> [!nav] 页面导航
> 首次主线 7/11 · [[01_学习指南/02_测试与实验复现/00 测试与实验复现学习地图#学习顺序|单元 02：测试与实验复现]] · [[01_学习指南/01_Python工程化/逐讲学习/06 看懂报错并安全管理资源|上一讲]] · [[01_学习指南/11_LLM_API与Prompt/逐讲学习/01 发出一次安全的模型 API 请求|下一讲]]

## 学完后你会做到什么

你会知道测试不是“再写一遍程序”，而是用输入、动作和预期结果检查一个行为。你将能运行 pytest、读懂 `assert`、观察一次失败，并为数据处理函数写第一条测试。

本讲需要的前置知识只有：会调用函数、会读列表和字典。不会 pytest 没关系；测试框架就是帮助我们自动执行检查并汇总结果的工具。

## 1. 先理解测试在回答什么问题

假设 `count_statuses` 要把工单分成 `open` 和 `closed`。只在终端手动打印一次，能知道这一次看起来对不对，却不能保证以后修改代码仍然正确。测试把这个判断写成可重复执行的句子：

```text
给定三张工单 → 调用统计函数 → 结果应该是 open 1、closed 2
```

测试中的三个词可以这样理解：

- **输入（given）：** 准备给程序的数据。
- **动作（when）：** 调用要检查的函数。
- **预期（then）：** 我们认为正确的结果或错误。

测试不会证明所有输入都正确；它只证明写进测试的情况在当前版本仍满足约定。因此，好的测试要覆盖正常情况、边界情况和重要失败情况。

## 2. 第一次运行测试

在 VS Code 中打开 `01_学习指南/02_测试与实验复现/示例工程/`，打开终端，执行：

```powershell
..\..\..\.venv\Scripts\python.exe -m pytest -q
```

`-m pytest` 表示让当前 Python 找到并运行 pytest；`-q` 是较简洁的输出。第一次可能看到多条通过记录，例如：

```text
...........                                                              [100%]
11 passed in 0.12s
```

数字和耗时会变化。`passed` 表示测试中的断言都成功；退出码为 0 也表示命令成功。若提示找不到解释器，先按仓库根目录 README 准备共享环境。

## 3. 最小测试长什么样

打开 `tests/test_data.py`，先看这段：

```python
from reprokit.data import count_statuses


def test_count_statuses_returns_both_categories() -> None:
    rows = [{"status": "open"}, {"status": "closed"}, {"status": "closed"}]

    assert count_statuses(rows) == {"open": 1, "closed": 2}
```

逐段理解：

1. `from ... import ...` 导入被测函数。测试应该调用真实函数，而不是重新复制一份实现。
2. 函数名以 `test_` 开头，pytest 才会按默认规则发现它。
3. `rows` 是本次测试的输入。
4. `assert` 是断言：如果左右两边相等，测试继续；不相等，pytest 会指出实际值和预期值。
5. `-> None` 是类型说明，表示测试函数不返回业务结果；测试结果由断言和异常决定。

运行单个文件：

```powershell
..\..\..\.venv\Scripts\python.exe -m pytest tests/test_data.py -q
```

运行单个测试：

```powershell
..\..\..\.venv\Scripts\python.exe -m pytest tests/test_data.py::test_count_statuses_returns_both_categories -q
```

路径中的 `::` 表示“文件中的某个测试”。这在排查失败时很有用，因为不用每次运行整个测试集。

## 4. 故意让测试失败

把预期值临时改成 `{"open": 2, "closed": 1}`，再次运行单个测试。你会看到失败信息，其中通常包含：测试位置、期望值、实际值和差异。测试失败不是工具坏了，而是它成功发现了一个不符合预期的结果。

把预期值改回正确结果，再运行。这个“改错—观察—修复”的动作很重要：以后看到红色输出时，你应先读断言差异，不要立刻删掉测试。

## 5. 测试错误输入

程序不只要在正常输入下工作。示例工程规定状态只能是 `open` 或 `closed`，所以测试也要检查非法数据会得到明确错误：

```python
import pytest

from reprokit.data import InvalidTicket, count_statuses


def test_count_statuses_rejects_invalid_row() -> None:
    with pytest.raises(InvalidTicket):
        count_statuses([{"status": "pending"}])
```

`pytest.raises(InvalidTicket)` 表示“这里预期抛出这种异常”。如果没有异常，或异常类型不对，测试就失败。它比只写 `try/except` 更直接地表达了规则。

## 6. 动手操作

1. 运行全部测试，记录通过数量。
2. 在 `tests/test_data.py` 添加一张 `closed` 工单，更新预期结果并运行。
3. 把状态改成 `pending`，观察失败信息；再改回正确状态。
4. 新增一个测试，确认空列表返回 `{"open": 0, "closed": 0}`。

预期结果是：正常统计、非法状态和空输入都有独立测试；最后 `pytest -q` 全部通过。

## 7. 常见错误

- **没有发现测试：** 函数名不是 `test_` 开头，或文件名不是 `test_*.py`。
- **找不到 `reprokit`：** 当前共享环境没有安装本单元；在示例工程根目录运行 README 中的可编辑安装命令，并确认使用仓库根目录的 Python。
- **把字符串和字典混在一起比较：** `{"open": 1}` 与 `"open:1"` 是不同类型，先看函数实际返回值。
- **测试只检查“不报错”：** 不报错不代表结果正确，仍要断言具体输出。

## 8. 练习与答案解析

**跟做：** 为 `count_statuses` 写一个只含两张 `open` 工单的测试。

**独立：** 写测试确认缺少 `status` 的字典会抛出 `InvalidTicket`。

**迁移：** 为 `parse_tool_response` 写一条测试，输入 `{"answer": "已关闭"}`，预期返回 `已关闭`。

> [!example]- 参考思路（先完成再展开）
> 先导入被测函数和异常；测试名用 `test_` 开头；在函数中准备输入，调用函数并用 `assert` 比较。异常场景用 `with pytest.raises(InvalidTicket):` 包住调用。迁移练习同样遵循“输入—动作—预期”，只是被测模块换成 `reprokit.output`。

完成标准：你能单独运行一个测试，能解释一次断言失败，并能从零写出一个正常输入测试和一个异常测试。

## 本讲小结

测试把“我认为程序应该这样工作”写成可重复检查的代码。pytest 负责发现和运行测试；`assert` 检查结果；`pytest.raises` 检查预期异常。下一讲会减少重复准备数据，并系统覆盖多个边界输入。

## 继续学习

> [!next] 下一步
> [[01_学习指南/11_LLM_API与Prompt/逐讲学习/01 发出一次安全的模型 API 请求|首次主线下一步：发出一次安全的模型 API 请求]]

> [!info]- 练习与记录
> [[01_学习指南/02_测试与实验复现/示例工程/README#代码导航（VS Code）|查看源码]] · [[01_学习指南/02_测试与实验复现/示例工程/README#安装与一键检查|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 02：测试、代码质量与实验复现|本单元完成清单]]
> 按单元查阅时：[[01_学习指南/02_测试与实验复现/逐讲学习/02 用 fixture 和参数化覆盖边界|单元内下一讲]]
> [[00_学习路线/01 从零开始建立共同基础|回看首次学习阶段]]
