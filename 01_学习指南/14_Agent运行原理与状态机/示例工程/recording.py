"""录制与只读播放公开 trace；播放不接收任何真实工具执行器。"""

import json
from pathlib import Path

from state import ALLOWED_TRANSITIONS, AgentState, Status


def save_recording(state: AgentState, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as target:
        json.dump(
            {
                "schema_version": 1,
                "run_id": state.run_id,
                "task": state.task,
                "status": state.status.value,
                "steps": state.steps,
                "final_text": state.final_text,
                "trace": state.trace,
            },
            target,
            ensure_ascii=False,
            indent=2,
        )


def play_recording(path: Path) -> dict:
    with path.open(encoding="utf-8") as source:
        recording = json.load(source)
    if recording.get("schema_version") != 1:
        raise ValueError("不支持的 trace 版本")
    current_status = Status.READY
    observations = []
    final_text = None
    for sequence, event in enumerate(recording["trace"], start=1):
        if event["sequence"] != sequence or event["from"] != current_status.value:
            raise ValueError("trace 顺序/状态不连续")
        next_status = Status(event["to"])
        if next_status not in ALLOWED_TRANSITIONS.get(current_status, set()):
            raise ValueError("trace 有非法状态转移")
        if event["run_id"] != recording["run_id"]:
            raise ValueError("trace 混入其他 run_id")
        current_status = next_status
        if event["event"] == "tool_observation":
            observations.append(event["observation"])
        if event["event"] == "final_answer":
            final_text = event["text"]
    if (
        current_status.value != recording["status"]
        or final_text != recording["final_text"]
    ):
        raise ValueError("trace 与摘要不一致")
    return {
        "status": current_status.value,
        "final_text": final_text,
        "observations": observations,
    }
