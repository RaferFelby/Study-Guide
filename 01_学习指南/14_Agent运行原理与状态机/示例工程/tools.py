"""两个本地工具：读政策、写入内存工单。无网络和真实外部副作用。"""

from collections.abc import Callable
from dataclasses import dataclass

from state import ToolResult


@dataclass(frozen=True)
class Tool:
    execute: Callable[[dict], ToolResult]
    requires_confirmation: bool = False


def lookup_policy(arguments: dict) -> ToolResult:
    service = arguments.get("service")
    if not isinstance(service, str):
        return ToolResult(False, error_code="invalid_arguments")
    policies = {
        "storage": {"retention": "30 days", "citation": "storage.md#retention"},
        "compute": {"retention": "14 days", "citation": "compute.md#retention"},
    }
    if service not in policies:
        return ToolResult(False, error_code="not_found")
    return ToolResult(True, policies[service])


def make_tools(ticket_store: list[dict]) -> dict[str, Tool]:
    def create_ticket(arguments: dict) -> ToolResult:
        title = arguments.get("title")
        if not isinstance(title, str) or not title.strip():
            return ToolResult(False, error_code="invalid_arguments")
        ticket = {"ticket_id": f"DEMO-{len(ticket_store) + 1}", "title": title}
        ticket_store.append(ticket)
        return ToolResult(True, ticket)

    return {
        "lookup_policy": Tool(lookup_policy),
        "create_ticket": Tool(create_ticket, requires_confirmation=True),
    }
