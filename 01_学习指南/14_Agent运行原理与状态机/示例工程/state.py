"""Agent 的公开状态和动作；不记录模型内部推理。"""

from dataclasses import dataclass, field
from enum import StrEnum


class Status(StrEnum):
    READY = "ready"
    DECIDING = "deciding"
    WAITING_TOOL = "waiting_tool"
    OBSERVING = "observing"
    WAITING_CONFIRMATION = "waiting_confirmation"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STEP_LIMIT = "step_limit"
    LOOP_DETECTED = "loop_detected"


TERMINAL_STATUSES = {
    Status.COMPLETED,
    Status.FAILED,
    Status.CANCELLED,
    Status.STEP_LIMIT,
    Status.LOOP_DETECTED,
}


@dataclass(frozen=True)
class Action:
    kind: str
    tool_name: str = ""
    arguments: dict = field(default_factory=dict)
    final_text: str = ""


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    data: dict = field(default_factory=dict)
    error_code: str | None = None


@dataclass
class AgentState:
    task: str
    run_id: str
    status: Status = Status.READY
    steps: int = 0
    final_text: str | None = None
    messages: list[dict] = field(default_factory=list)
    tool_records: list[dict] = field(default_factory=list)
    trace: list[dict] = field(default_factory=list)
    executed_actions: set[str] = field(default_factory=set)
    pending_action: Action | None = None
    approved_action_key: str | None = None


ALLOWED_TRANSITIONS = {
    Status.READY: {
        Status.DECIDING,
        Status.WAITING_TOOL,
        Status.CANCELLED,
        Status.STEP_LIMIT,
    },
    Status.DECIDING: {
        Status.WAITING_TOOL,
        Status.WAITING_CONFIRMATION,
        Status.COMPLETED,
        Status.FAILED,
        Status.CANCELLED,
        Status.LOOP_DETECTED,
    },
    Status.WAITING_TOOL: {Status.OBSERVING, Status.FAILED},
    Status.OBSERVING: {Status.READY, Status.FAILED},
    Status.WAITING_CONFIRMATION: {Status.READY, Status.CANCELLED},
}


def transition(state: AgentState, next_status: Status, event: str, **details) -> None:
    if next_status not in ALLOWED_TRANSITIONS.get(state.status, set()):
        raise ValueError(f"非法状态转移：{state.status} → {next_status}")
    state.trace.append(
        {
            "sequence": len(state.trace) + 1,
            "run_id": state.run_id,
            "step": state.steps,
            "from": state.status.value,
            "to": next_status.value,
            "event": event,
            **details,
        }
    )
    state.status = next_status
