"""可预测的规则决策器；教学时用它看清循环，不冒充真实模型。"""

from state import Action, AgentState


def policy_lookup(state: AgentState) -> Action:
    if not state.tool_records:
        return Action("tool", "lookup_policy", {"service": "storage"})
    observation = state.tool_records[-1]["result"]
    if not observation["ok"]:
        return Action("final", final_text="没有找到可用政策，无法回答。")
    data = observation["data"]
    return Action(
        "final", final_text=f"存储保留 {data['retention']}，依据 {data['citation']}。"
    )


def policy_ticket(state: AgentState) -> Action:
    if not state.tool_records:
        return Action("tool", "create_ticket", {"title": "请核实存储保留政策"})
    observation = state.tool_records[-1]["result"]
    if not observation["ok"]:
        return Action("final", final_text="创建演示工单失败。")
    return Action("final", final_text=f"演示工单：{observation['data']['ticket_id']}")


def policy_repeat(state: AgentState) -> Action:
    return Action("tool", "lookup_policy", {"service": "storage"})
