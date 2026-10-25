"""合成目录只读工具；模型文本不成为任意可执行命令。"""

TOOLS = {"color": "get_color", "size": "get_size", "shape": "get_shape"}


class ToolUnavailable(RuntimeError):
    pass


def make_catalog(changed=False):
    catalog = {}
    for index in range(7):
        color = "red" if index % 2 == 0 else "blue"
        size = "small" if index % 2 == 0 else "large"
        if changed:
            color = "blue" if color == "red" else "red"
            size = "large" if size == "small" else "small"
        catalog[f"item-{index}"] = {"color": color, "size": size, "shape": "round"}
    return catalog


def parse_call(tokens):
    if (
        not isinstance(tokens, list)
        or len(tokens) != 6
        or any(not isinstance(token, str) for token in tokens)
    ):
        raise ValueError("调用需为6个文本token")
    if (
        tokens[0] != "plan"
        or tokens[1] not in TOOLS
        or tokens[2] != "call"
        or tokens[-1] != "<eos>"
    ):
        raise ValueError("调用格式不符")
    if tokens[3] not in TOOLS.values() or tokens[4] not in make_catalog():
        raise ValueError("工具或参数不在固定允许范围")
    return {"plan": tokens[1], "tool": tokens[3], "entity_id": tokens[4]}


def semantic_checks(call, task):
    return {
        "plan_correct": call["plan"] == task["intent"],
        "tool_correct": call["tool"] == TOOLS[task["intent"]],
        "argument_correct": call["entity_id"] == task["entity_id"],
    }


def execute_tool(tool, entity_id, catalog, unavailable=False):
    if tool not in TOOLS.values() or entity_id not in catalog:
        raise ValueError("工具名称或实体ID不在固定范围")
    if unavailable:
        raise ToolUnavailable("synthetic_unavailable")
    attribute = next(name for name, tool_name in TOOLS.items() if tool_name == tool)
    return catalog[entity_id][attribute]
