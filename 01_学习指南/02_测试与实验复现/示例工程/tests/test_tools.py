from reprokit.tools import FakeTool, RateLimited, ToolTimeout, fetch_many


def test_fetch_many_keeps_success_when_one_tool_times_out() -> None:
    tool = FakeTool(
        responses={"A": '{"answer": "已关闭"}', "B": '{"answer": "处理中"}'},
        failures={"B": ToolTimeout()},
    )

    assert fetch_many(tool, ["A", "B"]) == {
        "A": '{"answer": "已关闭"}',
        "B": "unavailable",
    }


def test_fetch_many_handles_rate_limit() -> None:
    tool = FakeTool(responses={"A": "ok"}, failures={"A": RateLimited()})

    assert fetch_many(tool, ["A"]) == {"A": "unavailable"}
