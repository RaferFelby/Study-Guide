from dataclasses import dataclass
from typing import Protocol


class ToolTimeout(TimeoutError):
    """模拟工具超时。"""


class RateLimited(RuntimeError):
    """模拟服务限流。"""


class TicketTool(Protocol):
    def fetch(self, ticket_id: str) -> str: ...


@dataclass
class FakeTool:
    """可在测试中控制返回值或故障。"""

    responses: dict[str, str]
    failures: dict[str, Exception] | None = None

    def fetch(self, ticket_id: str) -> str:
        failure = (self.failures or {}).get(ticket_id)
        if failure is not None:
            raise failure
        return self.responses[ticket_id]


def fetch_many(tool: TicketTool, ticket_ids: list[str]) -> dict[str, str]:
    """逐个调用工具；单个失败时保留其他成功结果。"""
    results: dict[str, str] = {}
    for ticket_id in ticket_ids:
        try:
            results[ticket_id] = tool.fetch(ticket_id)
        except (ToolTimeout, RateLimited):
            results[ticket_id] = "unavailable"
    return results
