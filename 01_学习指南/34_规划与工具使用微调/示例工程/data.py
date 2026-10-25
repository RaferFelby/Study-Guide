"""显式合成轨迹、分组和错误隔离；不收集个人对话。"""

import copy

import torch

from tools import TOOLS, execute_tool, make_catalog, parse_call, semantic_checks

TOKENS = (
    [
        "<pad>",
        "<eos>",
        "query",
        "color",
        "size",
        "shape",
        "plan",
        "call",
        "get_color",
        "get_size",
        "get_shape",
        "observation",
        "final",
        "red",
        "blue",
        "small",
        "large",
        "round",
        "chat",
        "error",
        "unavailable",
        "refuse",
    ]
    + [f"item-{index}" for index in range(7)]
    + [f"case-{index:02d}" for index in range(36)]
    + ["case-unseen"]
)
TOKEN_IDS = {token: index for index, token in enumerate(TOKENS)}
PAD_ID, EOS_ID = 0, 1


def encode(tokens):
    if not isinstance(tokens, list) or any(
        not isinstance(token, str) or token not in TOKEN_IDS for token in tokens
    ):
        raise ValueError("输入需为固定词表token列表")
    return [TOKEN_IDS[token] for token in tokens]


def make_tasks(split="train"):
    groups = {"train": range(24), "dev": range(24, 30), "test": range(30, 36)}
    if split not in groups:
        raise ValueError("切分需为train/dev/test")
    return [
        {
            "source_id": f"case-{index:02d}",
            "intent": intent,
            "entity_id": f"item-{index % 6}",
            "prompt": ["query", intent, f"item-{index % 6}", f"case-{index:02d}"],
        }
        for index in groups[split]
        for intent in ("color", "size")
    ]


def make_trace(task):
    action = [
        "plan",
        task["intent"],
        "call",
        TOOLS[task["intent"]],
        task["entity_id"],
        "<eos>",
    ]
    observation = execute_tool(action[3], action[4], make_catalog())
    return {
        "source_id": task["source_id"],
        "task": copy.deepcopy(task),
        "action": action,
        "observation": observation,
        "answer": ["final", observation, "<eos>"],
        "origin": "synthetic_verified_rule",
        "usage_policy": "local_teaching_only",
    }


def validate_trace(trace):
    if not isinstance(trace, dict) or set(trace) != {
        "source_id",
        "task",
        "action",
        "observation",
        "answer",
        "origin",
        "usage_policy",
    }:
        raise ValueError("轨迹字段不符")
    if (
        trace["origin"] != "synthetic_verified_rule"
        or trace["usage_policy"] != "local_teaching_only"
        or trace["source_id"] != trace["task"]["source_id"]
    ):
        raise ValueError("来源声明不符")
    call = parse_call(trace["action"])
    if not all(semantic_checks(call, trace["task"]).values()):
        raise ValueError("轨迹语义不符")
    observed = execute_tool(call["tool"], call["entity_id"], make_catalog())
    if trace["observation"] != observed or trace["answer"] != [
        "final",
        observed,
        "<eos>",
    ]:
        raise ValueError("观察或最终答案不符")
    return trace


def prepare_traces():
    raw = [make_trace(task) for task in make_tasks()]
    for mode in ("wrong_tool", "wrong_argument", "wrong_observation", "wrong_answer"):
        bad = copy.deepcopy(raw[0])
        if mode == "wrong_tool":
            bad["action"][3] = "get_size"
        elif mode == "wrong_argument":
            bad["action"][4] = "item-1"
        elif mode == "wrong_observation":
            bad["observation"] = "blue"
        else:
            bad["answer"] = ["final", "blue", "<eos>"]
        raw.append(bad)
    valid, rejected = [], []
    for index, trace in enumerate(raw):
        try:
            validate_trace(trace)
            valid.append(trace)
        except ValueError as error:
            rejected.append(
                {
                    "raw_index": index,
                    "source_id": trace["source_id"],
                    "reason": str(error),
                }
            )
    return raw, valid, rejected


def make_training_rows(include_chat=False):
    _, traces, _ = prepare_traces()
    rows = []
    for trace in traces:
        task = trace["task"]
        rows.append((task["prompt"], trace["action"]))
        context = (
            task["prompt"] + trace["action"] + ["observation", trace["observation"]]
        )
        rows.append((context, trace["answer"]))
    # 正确拒答另建样本，不把错误调用本身当正标签。
    for trace in traces[:12]:
        context = trace["task"]["prompt"] + trace["action"] + ["error", "unavailable"]
        rows.append((context, ["refuse", "unavailable", "<eos>"]))
    if include_chat:
        rows.extend(chat_rows() * 4)
    return rows


def chat_rows():
    return [(["chat", color], [color, "<eos>"]) for color in ("red", "blue")]


def batch_rows(rows, device="cpu"):
    if not rows:
        raise ValueError("训练行不能为空")
    sequences, targets = [], []
    for prompt, answer in rows:
        if (
            not prompt
            or not answer
            or answer[-1] != "<eos>"
            or len(prompt) + len(answer) > 24
        ):
            raise ValueError("空样本、缺EOS或超上下文")
        sequences.append(encode(prompt + answer))
        targets.append([-100] * len(prompt) + encode(answer))
    width = max(map(len, sequences))
    inputs = torch.full((len(rows), width), PAD_ID, dtype=torch.long, device=device)
    labels = torch.full_like(inputs, -100)
    for index, (sequence, target) in enumerate(zip(sequences, targets, strict=True)):
        inputs[index, : len(sequence)] = torch.tensor(sequence, device=device)
        labels[index, : len(target)] = torch.tensor(target, device=device)
    return inputs, labels
