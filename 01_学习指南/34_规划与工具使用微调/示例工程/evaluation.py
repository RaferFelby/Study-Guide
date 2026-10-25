"""真实模型动作→受控工具→实际观察→模型答案，分层统计。"""

from data import chat_rows, make_tasks
from model import generate
from tools import (
    ToolUnavailable,
    execute_tool,
    make_catalog,
    parse_call,
    semantic_checks,
)


def run_episode(model, task, catalog=None, unavailable=False):
    catalog = make_catalog() if catalog is None else catalog
    action = generate(model, task["prompt"])
    result = {
        "source_id": task["source_id"],
        "action": action,
        "format_valid": False,
        "plan_correct": False,
        "tool_correct": False,
        "argument_correct": False,
        "semantic_valid": False,
        "execution_success": False,
        "end_to_end": False,
        "tool_calls": 0,
        "status": "invalid_format",
        "observation": None,
        "answer": [],
    }
    try:
        call = parse_call(action)
    except ValueError:
        return result
    result["format_valid"] = True
    result.update(semantic_checks(call, task))
    result["semantic_valid"] = all(
        result[key] for key in ("plan_correct", "tool_correct", "argument_correct")
    )
    if not result["semantic_valid"]:
        result["status"] = "semantic_rejected"
        return result
    # 语义未通过不执行；没有替模型修正工具名或参数。
    result["tool_calls"] = 1
    try:
        observation = execute_tool(
            call["tool"], call["entity_id"], catalog, unavailable
        )
    except ToolUnavailable:
        context = task["prompt"] + action + ["error", "unavailable"]
        result["answer"] = generate(model, context)
        result["status"] = "unavailable"
        return result
    result["execution_success"] = True
    result["observation"] = observation
    context = task["prompt"] + action + ["observation", observation]
    result["answer"] = generate(model, context)
    result["end_to_end"] = result["answer"] == ["final", observation, "<eos>"]
    result["status"] = "completed" if result["end_to_end"] else "answer_wrong"
    return result


def summarize(episodes):
    keys = (
        "format_valid",
        "plan_correct",
        "tool_correct",
        "argument_correct",
        "semantic_valid",
        "execution_success",
        "end_to_end",
    )
    return {
        "n": len(episodes),
        **{key: sum(item[key] for item in episodes) for key in keys},
        "tool_calls": sum(item["tool_calls"] for item in episodes),
        "details": episodes,
    }


def evaluate_model(model):
    tasks = make_tasks("test")
    normal = summarize([run_episode(model, task) for task in tasks])
    changed = summarize(
        [run_episode(model, task, make_catalog(True)) for task in tasks]
    )
    offline = [run_episode(model, task, unavailable=True) for task in tasks[:2]]
    unseen_tool = [
        {
            "source_id": f"probe-shape-{index}",
            "intent": "shape",
            "entity_id": f"item-{index}",
            "prompt": ["query", "shape", f"item-{index}", "case-unseen"],
        }
        for index in range(6)
    ]
    unseen_entity = [
        {
            "source_id": f"probe-entity-{intent}",
            "intent": intent,
            "entity_id": "item-6",
            "prompt": ["query", intent, "item-6", "case-unseen"],
        }
        for intent in ("color", "size")
    ]
    chat = [
        {"prompt": prompt, "answer": generate(model, prompt), "expected": answer}
        for prompt, answer in chat_rows()
    ]
    return {
        "normal": normal,
        "changed_catalog": changed,
        "unseen_tool": summarize([run_episode(model, task) for task in unseen_tool]),
        "unseen_entity": summarize(
            [run_episode(model, task) for task in unseen_entity]
        ),
        "offline": offline,
        "old_chat": {
            "n": len(chat),
            "correct": sum(row["answer"] == row["expected"] for row in chat),
            "details": chat,
        },
    }
