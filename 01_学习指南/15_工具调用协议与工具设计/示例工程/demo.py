import json

from contracts import ToolCall, ToolContext
from evaluation import evaluate_selector
from messages import execute_calls, make_assistant_message, validate_tool_message
from runtime import ToolRuntime, call_fingerprint


def main() -> None:
    runtime = ToolRuntime()
    calls = [
        ToolCall("call-1", "search_policies", '{"query":"storage retention","top_k":1}')
    ]
    context = ToolContext("demo-user", "staff")
    print(json.dumps(make_assistant_message(calls), ensure_ascii=False))
    pending_ids = {call.call_id for call in calls}
    for message in execute_calls(calls, runtime, context):
        validate_tool_message(message, pending_ids)
        print(json.dumps(message, ensure_ascii=False))
    arguments = {"title": "核实存储保留政策", "idempotency_key": "request-001"}
    write_call = ToolCall(
        "call-2", "create_ticket", json.dumps(arguments, ensure_ascii=False)
    )
    print("确认前：", runtime.execute(write_call, context))
    fingerprint = call_fingerprint(write_call.name, arguments, context.actor_id)
    approved_context = ToolContext(context.actor_id, "staff", frozenset({fingerprint}))
    print("确认后：", runtime.execute(write_call, approved_context))
    print("重复请求：", runtime.execute(write_call, context))
    print("实际内存工单数：", len(runtime.tickets))
    print("规则选择器评估：", evaluate_selector())


if __name__ == "__main__":
    main()
