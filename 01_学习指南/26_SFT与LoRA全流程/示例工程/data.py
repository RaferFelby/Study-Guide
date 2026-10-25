"""320条合成双格式指令样本；按来源组划分，词表预先定义。"""

import hashlib
import json

import torch

TOKENS = [
    "<pad>",
    "<eos>",
    "copy",
    "route",
    "classify",
    "red",
    "blue",
    "item",
    "answer",
    ":",
    "tag",
    "=",
    "R",
    "B",
] + [str(index) for index in range(80)]
TOKEN_TO_ID = {token: index for index, token in enumerate(TOKENS)}
PAD_ID = TOKEN_TO_ID["<pad>"]
EOS_ID = TOKEN_TO_ID["<eos>"]


def normalize_record(record):
    if not isinstance(record, dict):
        raise TypeError("每条数据需为字典")
    if set(record) == {"instruction", "input", "output", "source_group"}:
        if not all(
            isinstance(record[key], str) for key in ("instruction", "input", "output")
        ):
            raise ValueError("指令、输入、输出需为字符串")
        prompt = record["instruction"] + " " + record["input"]
        answer = record["output"]
    elif set(record) == {"messages", "source_group"}:
        messages = record["messages"]
        if (
            not isinstance(messages, list)
            or len(messages) != 2
            or not all(
                isinstance(message, dict) and set(message) == {"role", "content"}
                for message in messages
            )
            or messages[0].get("role") != "user"
            or messages[1].get("role") != "assistant"
        ):
            raise ValueError("本例messages仅接受一轮user/assistant")
        prompt = messages[0]["content"]
        answer = messages[1]["content"]
    elif set(record) == {"conversations", "source_group"}:
        conversations = record["conversations"]
        if (
            not isinstance(conversations, list)
            or len(conversations) != 2
            or not all(
                isinstance(turn, dict) and set(turn) == {"from", "value"}
                for turn in conversations
            )
            or conversations[0]["from"] != "human"
            or conversations[1]["from"] != "gpt"
        ):
            raise ValueError("本例ShareGPT风格仅接受一轮human/gpt")
        prompt = conversations[0]["value"]
        answer = conversations[1]["value"]
    else:
        raise ValueError("本例仅接受已说明的单轮指令或messages字段")
    if not all(
        isinstance(value, str) and value.strip()
        for value in (prompt, answer, record["source_group"])
    ):
        raise ValueError("文本和来源组需非空字符串")
    return {
        "prompt": prompt.split(),
        "answer": answer.split() + ["<eos>"],
        "source_group": record["source_group"],
    }


def make_records():
    records = []
    for group in range(80):
        for color in ("red", "blue"):
            for task in ("route", "classify"):
                records.append(
                    {
                        "instruction": task,
                        "input": f"{color} item {group} answer :",
                        "output": "tag = " + ("R" if color == "red" else "B"),
                        "source_group": f"item-{group:02d}",
                    }
                )
    return records


def split_records(records):
    splits = {"train": [], "validation": [], "test": []}
    seen = set()
    for record in records:
        normalized = normalize_record(record)
        signature = tuple(normalized["prompt"])
        if signature in seen:
            raise ValueError("重复输入需先清理，不能随机拆到不同集合")
        seen.add(signature)
        group = int(normalized["source_group"].removeprefix("item-"))
        if normalized["source_group"] != f"item-{group:02d}" or not 0 <= group < 80:
            raise ValueError("本例来源组需为item-00至item-79")
        name = "train" if group < 50 else "validation" if group < 65 else "test"
        splits[name].append(normalized)
    if any(not split for split in splits.values()):
        raise ValueError("训练/验证/测试集合不能空")
    groups = [{row["source_group"] for row in rows} for rows in splits.values()]
    if groups[0] & groups[1] or groups[0] & groups[2] or groups[1] & groups[2]:
        raise ValueError("来源组不能跨集合")
    return splits


def encode(tokens):
    try:
        return [TOKEN_TO_ID[token] for token in tokens]
    except KeyError as error:
        raise ValueError(f"固定词表不认识token：{error.args[0]}") from error


def make_batch(rows, device):
    sequences = [encode(row["prompt"] + row["answer"]) for row in rows]
    if not sequences:
        raise ValueError("批次不能空")
    length = max(len(sequence) - 1 for sequence in sequences)
    inputs = torch.full((len(rows), length), PAD_ID, dtype=torch.long, device=device)
    labels = torch.full_like(inputs, -100)
    for index, (row, sequence) in enumerate(zip(rows, sequences, strict=True)):
        inputs[index, : len(sequence) - 1] = torch.tensor(sequence[:-1], device=device)
        labels[index, : len(sequence) - 1] = torch.tensor(sequence[1:], device=device)
        # 位移后的第prompt_length-1位置才预测首个答案token。
        labels[index, : len(row["prompt"]) - 1] = -100
    return inputs, labels


def base_records(rows):
    result = []
    for row in rows:
        prompt = ["copy", *row["prompt"][1:]]
        result.append(
            {
                "prompt": prompt,
                "answer": [prompt[1], "<eos>"],
                "source_group": row["source_group"],
            }
        )
    return result


def dataset_digest(records):
    raw = json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
