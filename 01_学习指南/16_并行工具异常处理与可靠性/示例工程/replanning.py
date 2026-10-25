"""依据公开结构化结果提出下一步；不执行新操作或绕过授权。"""


def plan_next_actions(
    results: list[dict], conflicts: list[dict] | None = None
) -> list[dict]:
    conflicted_fields = {item["field"] for item in conflicts or []}
    plans = []
    for result in results:
        if result["ok"]:
            action = (
                "read_full_result"
                if result["data"]["is_summary"]
                else "use_observation"
            )
            if not result["data"]["is_summary"]:
                field = result["data"]["content"].get("field")
                if field in conflicted_fields:
                    action = "verify_source_conflict"
        else:
            code = result["error"]["code"]
            if code == "outcome_unknown":
                action = "verify_write_status"
            elif code == "invalid_arguments_or_result":
                action = "repair_arguments_or_adapter"
            elif code in {"rate_limited", "circuit_open"}:
                action = "defer_or_use_authorized_fallback"
            elif code in {"timeout", "temporary_io_failure"}:
                action = "report_exhausted_attempts_or_choose_alternative"
            else:
                action = "report_unavailable"
        plans.append({"call_id": result["call_id"], "next_action": action})
    return plans
