---
title: 第 3 讲：用 mock 注入工具故障
aliases:
  - 测试与实验复现 03
  - mock、超时与限流
tags:
  - curriculum
  - python
  - testing
  - reliability
status: published
updated: 2026-10-25
cssclasses: ["learning-note", "guide-page", "guide-lesson"]
---

# 第 3 讲：用 mock 注入工具故障

> [!nav] 页面导航
> [[01_学习指南/02_测试与实验复现/00 测试与实验复现学习地图#学习顺序|单元 02：测试与实验复现]] · [[01_学习指南/02_测试与实验复现/逐讲学习/02 用 fixture 和参数化覆盖边界|上一讲]] · [[01_学习指南/02_测试与实验复现/逐讲学习/04 选择合适的测试层级|下一讲]]

## 学完后你会做到什么

你会知道 mock 是测试中的“可控替身”：它让我们不用等待真实网络服务，也能安排依赖返回数据或抛出特定错误。本讲会覆盖超时、限流、非法 JSON 和部分工具失败，对应验收标准 C03-02。

## 1. 为什么不能每次都调用真实服务

真实服务可能慢、收费、需要账号，或者今天恰好不可用。更重要的是，真实服务很难稳定地“刚好在这一刻超时一次”。如果故障分支没有测试，代码上线后才遇到限流，才发现处理方式不清楚。

mock 的目标不是假装真实服务永远正常，而是把依赖行为变成测试可以控制的输入。它的局限也要记住：mock 只能验证我们预设的合同，不能证明真实服务的协议没有变化。因此仍需要少量集成测试。

## 2. 先看示例工程的依赖边界

打开 `src/reprokit/tools.py`：`TicketTool` 协议只要求有一个 `fetch(ticket_id)` 方法；`fetch_many` 负责逐个调用，并把 `ToolTimeout` 或 `RateLimited` 转成 `unavailable`。这是一条明确的测试边界：工具本身怎样访问网络不是本模块要测的；本模块要测的是成功和可预期故障如何被整理。

## 3. 用 Fake 对象安排故障

示例中的 `FakeTool` 是一个手写的测试替身：

```python
tool = FakeTool(
    responses={"A": '{"answer": "已关闭"}'},
    failures={"B": ToolTimeout()},
)

assert fetch_many(tool, ["A", "B"]) == {
    "A": '{"answer": "已关闭"}',
    "B": "unavailable",
}
```

它比真实网络客户端简单，但方法名和输入形状相同，所以可以交给 `fetch_many`。A 成功保留响应，B 抛出超时后被整理成 `unavailable`。这就是“部分失败”：一个工具失败不应自动丢掉已经成功的结果。

手写 Fake 的优点是行为容易读、类型清楚；当只需替换一个方法或检查调用次数时，pytest 的 `monkeypatch` 和 `Mock` 会更方便。

## 4. 用 monkeypatch 临时替换行为

`monkeypatch` 是 pytest 提供的 fixture，可以在测试期间替换属性，测试结束后自动恢复：

```python
from reprokit import tools


def test_timeout_is_converted(monkeypatch) -> None:
    def always_timeout(self, ticket_id: str) -> str:
        raise tools.ToolTimeout()

    monkeypatch.setattr(tools.FakeTool, "fetch", always_timeout)
    tool = tools.FakeTool(responses={"A": "unused"})

    assert tools.fetch_many(tool, ["A"]) == {"A": "unavailable"}
```

替换只在当前测试有效，不会永久修改源码。`self` 是实例方法的第一个参数；`ticket_id` 保留原方法需要的输入。测试结束后 pytest 清理替换，后面的测试不会意外继承这个故障。

## 5. mock 调用次数和输入

若安装并使用 `unittest.mock.Mock`，可以把返回值或副作用写出来：

```python
from unittest.mock import Mock

from reprokit.tools import fetch_many


def test_tool_receives_each_id() -> None:
    tool = Mock()
    tool.fetch.side_effect = ["one", "two"]

    assert fetch_many(tool, ["A", "B"]) == {"A": "one", "B": "two"}
    assert tool.fetch.call_count == 2
    tool.fetch.assert_any_call("A")
    tool.fetch.assert_any_call("B")
```

`side_effect` 让连续调用得到不同结果；`call_count` 检查调用次数；`assert_any_call` 检查具体参数。不要只断言“调用过”，还要断言结果；也不要把实现细节锁得过死，例如没有必要规定内部一定使用某个循环。

## 6. 非法 JSON 是另一层错误

打开 `src/reprokit/output.py`。`parse_tool_response` 负责把工具返回的文本解析成答案，不负责发起工具调用。测试可以直接提供三类输入：普通文字不是 JSON、空对象缺少 `answer`、`answer` 不是字符串：

```python
@pytest.mark.parametrize("text", ["not-json", "{}", '{"answer": 7}'])
def test_bad_response_is_rejected(text: str) -> None:
    with pytest.raises(InvalidToolResponse):
        parse_tool_response(text)
```

把“调用工具”和“解析输出”分开，故障测试更容易定位：如果测试失败，是调用策略错了，还是响应结构校验错了，不会混成一个大函数。

## 7. 动手操作

1. 运行 `tests/test_tools.py`，确认超时和限流测试通过。
2. 新增一个 `FakeTool`，让 A 抛出 `RateLimited`、B 正常返回，确认结果只把 A 标记为 `unavailable`。
3. 在 `tests/test_output.py` 增加参数化非法 JSON 测试。
4. 临时把 `fetch_many` 中的 `except` 改成只捕获 `ToolTimeout`，运行测试，观察限流测试如何提醒你漏掉了一条故障合同；然后恢复代码。

## 8. 常见错误

- **mock 的位置替换错了：** 应替换“被测代码实际查找的名字”，不是盲目替换依赖原始定义所在的文件。
- **捕获 `Exception`：** 会把编程错误也吞掉；只捕获业务上明确可以恢复的异常。
- **只测试 mock，不测试被测函数：** mock 是输入控制工具，真正的断言仍应落在业务结果上。
- **把超时当成远端一定没执行：** 本地等待超时不等于远端操作撤销；测试应明确这个边界。

## 9. 练习与答案解析

**跟做：** 用 `FakeTool` 模拟一个超时和一个成功，断言成功结果仍保留。

**独立：** 用参数化测试分别模拟 `ToolTimeout` 和 `RateLimited`，确认两者都得到 `unavailable`。

**迁移：** 为输出解析增加“`answer` 为空字符串”的规则。先决定空字符串是否允许，再写测试和实现；不要让测试替你决定业务规则。

> [!example]- 参考思路（先完成再展开）
> 故障注入的输入是异常类型，测试的预期是错误被转化后的结果。若业务决定空答案非法，应在 `parse_tool_response` 中增加 `value["answer"].strip()` 的检查，并用 `pytest.raises(InvalidToolResponse)` 锁定该规则；若空答案合法，则测试应断言返回空字符串。

完成标准：能说明 Fake、monkeypatch 和 Mock 的用途差异；能独立测试超时、限流、非法 JSON 与部分失败；能说出 mock 测试不能替代真实集成测试的原因。

## 本讲小结

mock 让不可控的外部依赖变成可安排的测试输入。手写 Fake 适合表达简单合同；monkeypatch 适合临时替换；Mock 还能检查调用。下一讲学习如何决定哪些行为放在单元、集成或端到端测试中。

## 继续学习

> [!next] 下一步
> [[01_学习指南/02_测试与实验复现/逐讲学习/04 选择合适的测试层级|下一讲：选择合适的测试层级]]

> [!info]- 练习与记录
> [[01_学习指南/02_测试与实验复现/示例工程/README#代码导航（VS Code）|查看源码]] · [[01_学习指南/02_测试与实验复现/示例工程/README#安装与一键检查|运行命令]] · [[02_学习记录/01 全课程完成清单#单元 02：测试、代码质量与实验复现|本单元完成清单]]
