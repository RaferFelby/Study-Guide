"""固定词表、合成偏好与来源组；没有真实人工偏好或模型生成。"""

import torch

TOKENS = ["<pad>", "<eos>", "red", "blue", "ask", "copy", "item", "ok", "detail"] + [
    f"id-{index:02d}" for index in range(36)
]
TOKEN_IDS = {token: index for index, token in enumerate(TOKENS)}
PAD_ID, EOS_ID = 0, 1


def encode(tokens):
    if not isinstance(tokens, list) or any(
        not isinstance(token, str) or token not in TOKEN_IDS for token in tokens
    ):
        raise ValueError("使用本工程固定词表的token列表")
    return [TOKEN_IDS[token] for token in tokens]


def make_pairs(split="train", biased=False):
    groups = {"train": range(24), "dev": range(24, 30), "test": range(30, 36)}
    if split not in groups or type(biased) is not bool:
        raise ValueError("切分或偏差开关不合法")
    pairs = []
    for index in groups[split]:
        for color in ("red", "blue"):
            other = "blue" if color == "red" else "red"
            pairs.append(
                {
                    "source_id": f"source-{index:02d}",
                    "color": color,
                    "prompt": ["ask", color, "item", f"id-{index:02d}"],
                    "chosen": ["ok", other if biased else color, "<eos>"],
                    "rejected": ["ok", color, "detail", "detail", "<eos>"],
                    "preference_origin": "deliberately_wrong_short_fixture"
                    if biased
                    else "synthetic_brief_style_rule",
                    "usage_policy": "local_teaching_only",
                }
            )
    return pairs


def validate_pair(pair):
    if not isinstance(pair, dict) or set(pair) != {
        "source_id",
        "color",
        "prompt",
        "chosen",
        "rejected",
        "preference_origin",
        "usage_policy",
    }:
        raise ValueError("偏好字段不合法")
    if pair["color"] not in {"red", "blue"} or not isinstance(pair["source_id"], str):
        raise ValueError("来源或颜色不合法")
    if pair["usage_policy"] != "local_teaching_only" or pair[
        "preference_origin"
    ] not in {"synthetic_brief_style_rule", "deliberately_wrong_short_fixture"}:
        raise ValueError("来源使用范围或偏好依据未声明")
    for field in ("prompt", "chosen", "rejected"):
        encode(pair[field])
    if (
        len(pair["prompt"]) != 4
        or pair["prompt"][:3] != ["ask", pair["color"], "item"]
        or pair["prompt"][3].replace("id-", "source-") != pair["source_id"]
    ):
        raise ValueError("问题与来源不一致")
    if not pair["chosen"] or not pair["rejected"] or pair["chosen"] == pair["rejected"]:
        raise ValueError("不能使用空回答或相同回答作为有方向偏好")
    if any(
        answer[-1] != "<eos>" or len(answer) > 8
        for answer in (pair["chosen"], pair["rejected"])
    ):
        raise ValueError("回答需有EOS且不超过8token")
    return pair


def batch_sequences(prompts, completions, device="cpu"):
    if not prompts or len(prompts) != len(completions):
        raise ValueError("问题和回答批量必须非空且对应")
    sequences, target_lists = [], []
    for prompt, completion in zip(prompts, completions, strict=True):
        if (
            not prompt
            or not completion
            or completion[-1] != "<eos>"
            or len(prompt) + len(completion) > 16
        ):
            raise ValueError("空输入、缺EOS或超过教学上下文")
        sequence = encode(prompt + completion)
        sequences.append(sequence)
        target_lists.append([-100] * len(prompt) + encode(completion))
    width = max(map(len, sequences))
    inputs = torch.full(
        (len(sequences), width), PAD_ID, dtype=torch.long, device=device
    )
    labels = torch.full_like(inputs, -100)
    for row, (sequence, targets) in enumerate(
        zip(sequences, target_lists, strict=True)
    ):
        inputs[row, : len(sequence)] = torch.tensor(sequence, device=device)
        labels[row, : len(sequence)] = torch.tensor(targets, device=device)
    return inputs, labels
