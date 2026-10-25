"""评估规则调用选择器，区分名称、参数与最终业务结果。"""

import json

from contracts import ToolCall, ToolContext
from runtime import ToolRuntime

CASES = [
    {
        "task": "查询存储保留政策",
        "gold_tool": "search_policies",
        "gold_arguments": {"query": "storage retention", "top_k": 1},
        "gold_evidence": "storage-retention",
    },
    {
        "task": "查询计算保留政策",
        "gold_tool": "search_policies",
        "gold_arguments": {"query": "compute retention", "top_k": 1},
        "gold_evidence": "compute-retention",
    },
    {
        "task": "查询数据库保留政策",
        "gold_tool": "search_policies",
        "gold_arguments": {"query": "database retention", "top_k": 1},
        "gold_evidence": "database-retention",
    },
    {
        "task": "查询存储，返回两条",
        "gold_tool": "search_policies",
        "gold_arguments": {"query": "storage retention", "top_k": 2},
        "gold_evidence": "storage-retention",
    },
]


def choose_call(task: str, call_id: str) -> ToolCall:
    # 已解释的确定规则，不使用gold字段，不冒充LLM。
    service = "storage"
    if "计算" in task:
        service = "compute"
    if "数据库" in task:
        service = "database"
    # 故意尚未支持“两条”，让参数指标发现遗漏。
    arguments = {"query": f"{service} retention", "top_k": 1}
    return ToolCall(call_id, "search_policies", json.dumps(arguments))


def evaluate_selector() -> dict:
    runtime = ToolRuntime()
    context = ToolContext("evaluation-user", "staff")
    rows = []
    for index, case in enumerate(CASES, start=1):
        call = choose_call(case["task"], f"eval-{index}")
        result = runtime.execute(call, context)
        arguments = json.loads(call.arguments_json)
        name_correct = call.name == case["gold_tool"]
        arguments_correct = name_correct and arguments == case["gold_arguments"]
        evidence_ids = (
            [item["id"] for item in result["data"]["evidence"]] if result["ok"] else []
        )
        # 本任务的业务标准同时要求返回预算被遵守。
        completed = arguments_correct and case["gold_evidence"] in evidence_ids
        rows.append(
            {
                "task": case["task"],
                "name_correct": name_correct,
                "arguments_correct": arguments_correct,
                "completed": completed,
            }
        )
    return {
        "cases": len(rows),
        "tool_selection_accuracy": sum(row["name_correct"] for row in rows) / len(rows),
        "argument_accuracy": sum(row["arguments_correct"] for row in rows) / len(rows),
        "task_completion_rate": sum(row["completed"] for row in rows) / len(rows),
        "rows": rows,
    }
