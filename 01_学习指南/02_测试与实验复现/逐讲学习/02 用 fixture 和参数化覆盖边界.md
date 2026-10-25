---
title: 第 2 讲：用 fixture 和参数化覆盖边界
aliases:
  - 测试与实验复现 02
  - fixture 与参数化
tags:
  - curriculum
  - python
  - testing
status: published
updated: 2026-10-25
cssclasses: ["learning-note", "guide-page", "guide-lesson"]
---

# 第 2 讲：用 fixture 和参数化覆盖边界

> [!nav] 页面导航
> [[01_学习指南/02_测试与实验复现/00 测试与实验复现学习地图#学习顺序|单元 02：测试与实验复现]] · [[01_学习指南/02_测试与实验复现/逐讲学习/01 写第一个 pytest 测试|上一讲]] · [[01_学习指南/02_测试与实验复现/逐讲学习/03 用 mock 注入工具故障|下一讲]]

## 学完后你会做到什么

你会知道 fixture 是可复用的测试准备步骤，参数化是用多组输入重复运行同一测试。两者都不是为了少写几行而已，更重要的是让测试意图清晰、边界不容易漏掉。

## 1. 为什么要复用准备数据

当多个测试都需要同样的工单列表时，直接在每个函数里复制列表会有两个问题：一处修改后另一处可能忘记同步；测试主体被准备数据淹没。fixture 把准备工作取出，测试函数通过参数拿到准备好的值。

最小例子：

```python
import pytest


@pytest.fixture
def sample_rows() -> list[dict[str, object]]:
    return [{"status": "open"}, {"status": "closed"}]


def test_has_two_rows(sample_rows: list[dict[str, object]]) -> None:
    assert len(sample_rows) == 2
```

`@pytest.fixture` 告诉 pytest：这是一个准备函数；测试函数参数名与 fixture 名相同，pytest 会在运行测试前调用它并传入返回值。类比为“每次考试前发一份新的草稿纸”，但实际机制是 pytest 管理调用与依赖，不是全局变量。

fixture 默认每个测试函数执行一次。这样一个测试对列表的修改不会污染下一个测试。共享可变数据时尤其重要。

## 2. 参数化：同一规则检查多组数据

下面三个输入都应被拒绝：缺字段、未知状态、错误类型。若分别写三个几乎一样的测试，主体重复；参数化让 pytest 为每组参数生成一个独立测试实例：

```python
import pytest

from reprokit.data import InvalidTicket, count_statuses


@pytest.mark.parametrize(
    "row",
    [{}, {"status": "pending"}, {"status": 3}],
)
def test_invalid_rows_are_rejected(row: dict[str, object]) -> None:
    with pytest.raises(InvalidTicket):
        count_statuses([row])
```

`"row"` 是参数名，后面的列表是参数值。pytest 会分别运行三次，失败时会显示参数值，方便定位是哪一组输入出问题。参数化不等于随机生成；这里的每个边界样例都是明确写下来的证据。

## 3. fixture 与参数化什么时候分别使用

- 准备一组很多测试都要用的环境或数据时，用 fixture。
- 同一个规则要检查多组输入时，用参数化。
- 一组数据同时变化多个字段时，可以把参数写成多个参数，或使用带名称的参数对象。
- 不要为了追求“少写代码”把所有内容都塞进 fixture；测试读者仍应容易看出输入是什么。

测试的可读性优先于抽象程度。初学阶段，重复一两行数据通常比绕过多层 fixture 更容易理解。

## 4. 测试可变对象的隔离

观察下面的 fixture：

```python
@pytest.fixture
def numbers() -> list[int]:
    return [1, 2, 3]


def test_append(numbers: list[int]) -> None:
    numbers.append(4)
    assert numbers == [1, 2, 3, 4]


def test_original_numbers(numbers: list[int]) -> None:
    assert numbers == [1, 2, 3]
```

两个测试各自得到新的列表，所以第一个测试的 `append` 不会影响第二个。若把列表写在模块顶层并让测试共同修改它，测试顺序就可能影响结果，这叫测试之间发生污染。污染会造成“单独运行通过、全部运行失败”这种难排查的问题。

## 5. 动手操作

在 `tests/test_data.py` 中完成：

1. 添加一个 `sample_rows` fixture，返回一张 `open` 和两张 `closed` 工单。
2. 让正常统计测试使用这个 fixture，不再在函数内部重复列表。
3. 添加参数化测试，覆盖空字典、`pending` 和数字状态。
4. 用单文件和全部测试各运行一次。

预期是每个参数化样例都显示为独立测试，最终全部通过。若某一组失败，pytest 的名称中应能看出输入值。

## 6. 常见错误

- **fixture 参数名拼错：** pytest 会提示找不到 fixture；检查测试函数参数和 fixture 函数名是否完全一致。
- **fixture 返回同一个全局列表：** 测试可能互相污染；在 fixture 内新建对象。
- **参数化参数数量不匹配：** 装饰器里的参数名数量必须和每组值的数量一致。
- **只测正常样例：** 外部输入最容易在缺字段、空值、边界数量处出错，至少为每条业务规则准备一个失败样例。

## 7. 练习与答案解析

**跟做：** 把 `test_count_statuses_returns_both_categories` 改为使用 fixture。

**独立：** 为 `parse_tool_response` 参数化三组非法文本：普通文字、空对象、`answer` 为数字。

**迁移：** 创建一个 fixture 返回 `FakeTool`，再参数化工具故障类型，检查调用结果是否变成 `unavailable`。

> [!example]- 参考思路（先完成再展开）
> fixture 只负责返回准备好的对象，参数化负责列出多个输入。不要在参数化数据中放异常实例然后直接让 pytest 抛出；用 `pytest.raises` 明确“预期异常”或让被测函数返回可断言的结果。工具练习会在下一讲完整讲解 mock 和故障注入。

完成标准：你能解释 fixture 的执行时机，能写一个参数化测试，并能说明为什么测试之间不应共享会被修改的列表。

## 本讲小结

fixture 管理可复用准备步骤，默认让每个测试拥有独立对象；参数化让一个规则覆盖多组明确输入。下一讲把这套方法用于没有真实服务也能测试的超时、限流和部分失败。

## 继续学习

> [!next] 下一步
> [[01_学习指南/02_测试与实验复现/逐讲学习/03 用 mock 注入工具故障|下一讲：用 mock 注入工具故障]]

> [!info]- 练习与记录
> [[01_学习指南/02_测试与实验复现/示例工程/README#代码导航（VS Code）|查看源码]] · [[01_学习指南/02_测试与实验复现/示例工程/README#安装与一键检查|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 02：测试、代码质量与实验复现|本单元完成清单]]
