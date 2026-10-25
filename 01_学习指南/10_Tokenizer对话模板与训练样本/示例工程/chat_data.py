"""把教学用对话结构转换为 token、训练标签和批次 mask。"""

from collections.abc import Sequence
from typing import TypedDict

from tokenizer import (
    BOS_ID,
    EOS_ID,
    IM_END_ID,
    IM_SEP_ID,
    IM_START_ID,
    PAD_ID,
    encode_text,
)

IGNORE_INDEX = -100
ALLOWED_ROLES = {"system", "user", "assistant", "tool"}


class Message(TypedDict, total=False):
    role: str
    content: str
    recipient: str


def encode_messages(
    messages: Sequence[Message], *, append_eos: bool = True
) -> tuple[list[int], list[int]]:
    """编码对话；只监督 assistant 正文和结束标记。"""
    if not messages:
        raise ValueError("messages 不能为空")

    input_ids = [BOS_ID]
    labels = [IGNORE_INDEX]

    for index, message in enumerate(messages):
        role = message.get("role")
        content = message.get("content")
        recipient = message.get("recipient")
        if role not in ALLOWED_ROLES:
            raise ValueError(f"不支持的 role：{role!r}")
        if not isinstance(content, str):
            raise TypeError("每条消息的 content 必须是字符串")
        if recipient is not None and (
            role != "assistant" or not isinstance(recipient, str)
        ):
            raise ValueError("recipient 只允许用于带字符串收件人的 assistant 消息")

        header = role if recipient is None else f"{role} to={recipient}"
        input_ids.extend([IM_START_ID, *encode_text(header), IM_SEP_ID])
        labels.extend([IGNORE_INDEX] * (len(header.encode("utf-8")) + 2))

        content_ids = encode_text(content)
        input_ids.extend(content_ids)
        if role == "assistant":
            labels.extend(content_ids)
        else:
            labels.extend([IGNORE_INDEX] * len(content_ids))

        input_ids.append(IM_END_ID)
        labels.append(IM_END_ID if role == "assistant" else IGNORE_INDEX)

        is_final_message = index == len(messages) - 1
        if append_eos and is_final_message and role == "assistant":
            input_ids.append(EOS_ID)
            labels.append(EOS_ID)

    return input_ids, labels


def pad_batch(
    examples: Sequence[tuple[Sequence[int], Sequence[int]]],
    *,
    padding_side: str = "right",
) -> dict[str, list[list[int]]]:
    """將 input 和 labels 補齊到同長度，並分別生成 attention mask。"""
    if not examples:
        raise ValueError("examples 不能为空")
    if padding_side not in {"left", "right"}:
        raise ValueError("padding_side 必须是 'left' 或 'right'")

    max_length = 0
    for input_ids, labels in examples:
        if len(input_ids) != len(labels):
            raise ValueError("每个样本的 input_ids 与 labels 长度必须相同")
        max_length = max(max_length, len(input_ids))

    batch_input_ids: list[list[int]] = []
    batch_labels: list[list[int]] = []
    attention_masks: list[list[int]] = []

    for input_ids, labels in examples:
        padding_length = max_length - len(input_ids)
        padding_ids = [PAD_ID] * padding_length
        ignored_labels = [IGNORE_INDEX] * padding_length
        valid_mask = [1] * len(input_ids)
        padding_mask = [0] * padding_length

        if padding_side == "right":
            batch_input_ids.append([*input_ids, *padding_ids])
            batch_labels.append([*labels, *ignored_labels])
            attention_masks.append([*valid_mask, *padding_mask])
        else:
            batch_input_ids.append([*padding_ids, *input_ids])
            batch_labels.append([*ignored_labels, *labels])
            attention_masks.append([*padding_mask, *valid_mask])

    return {
        "input_ids": batch_input_ids,
        "labels": batch_labels,
        "attention_mask": attention_masks,
    }


def count_supervised_tokens(labels: Sequence[int]) -> int:
    """统计未被忽略、会进入语言模型损失的标签数。"""
    return sum(label != IGNORE_INDEX for label in labels)
