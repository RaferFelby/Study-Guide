"""构造离线字符级数据，把每个 token 对齐到下一个 token 标签。"""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch.utils.data import DataLoader, Dataset

PAD_TOKEN = "<pad>"
PAD_TOKEN_ID = 0
RANDOM_SEED = 7

TRAIN_LINES = [
    "the cat sat on the mat.",
    "the dog sat on the rug.",
    "the cat met the dog.",
    "the dog met the cat.",
    "cats and dogs nap.",
    "the cat ran past the dog.",
    "the dog ran past the cat.",
]
VALIDATION_LINES = [
    "the cat sat and the dog ran.",
    "the dog sat and the cat ran.",
]


@dataclass(frozen=True)
class CharacterTokenizer:
    """把字符和整数 ID 双向转换；0 专门保留给 padding。"""

    token_to_id: dict[str, int]
    id_to_token: list[str]

    def encode(self, text: str) -> list[int]:
        unknown_tokens = sorted(set(text) - self.token_to_id.keys())
        if unknown_tokens:
            raise ValueError(
                f"text contains characters outside the vocabulary: {unknown_tokens}"
            )
        return [self.token_to_id[character] for character in text]

    def decode(self, token_ids: list[int]) -> str:
        if any(
            token_id < 0 or token_id >= len(self.id_to_token) for token_id in token_ids
        ):
            raise ValueError("token_ids contains an ID outside the vocabulary")
        return "".join(
            self.id_to_token[token_id]
            for token_id in token_ids
            if token_id != PAD_TOKEN_ID
        )


def build_character_tokenizer(training_text: str) -> CharacterTokenizer:
    """只从训练文本建立词表，并为 padding 预留 ID 0。"""
    if not training_text:
        raise ValueError("training_text cannot be empty")
    characters = sorted(set(training_text))
    id_to_token = [PAD_TOKEN, *characters]
    token_to_id = {token: token_id for token_id, token in enumerate(id_to_token)}
    return CharacterTokenizer(token_to_id, id_to_token)


class NextTokenDataset(Dataset[tuple[torch.Tensor, torch.Tensor]]):
    """用长度为 context_length 的窗口构造错开一格的输入与目标。"""

    def __init__(self, token_ids: list[int], context_length: int):
        if context_length < 1:
            raise ValueError("context_length must be positive")
        if len(token_ids) <= context_length:
            raise ValueError("token_ids must contain more than context_length tokens")

        token_tensor = torch.tensor(token_ids, dtype=torch.long)
        self.input_ids = torch.stack(
            [
                token_tensor[start : start + context_length]
                for start in range(len(token_ids) - context_length)
            ]
        )
        self.target_ids = torch.stack(
            [
                token_tensor[start + 1 : start + context_length + 1]
                for start in range(len(token_ids) - context_length)
            ]
        )

    def __len__(self) -> int:
        return len(self.input_ids)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        return self.input_ids[index], self.target_ids[index]


def make_data_loaders(
    context_length: int, batch_size: int
) -> tuple[CharacterTokenizer, DataLoader, DataLoader]:
    """用固定的本地文本建立训练与验证 DataLoader。"""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")

    training_text = "\n".join(TRAIN_LINES * 8)
    validation_text = "\n".join(VALIDATION_LINES * 4)
    tokenizer = build_character_tokenizer(training_text)
    train_dataset = NextTokenDataset(
        tokenizer.encode(training_text), context_length=context_length
    )
    validation_dataset = NextTokenDataset(
        tokenizer.encode(validation_text), context_length=context_length
    )
    shuffle_generator = torch.Generator().manual_seed(RANDOM_SEED)
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        generator=shuffle_generator,
    )
    validation_loader = DataLoader(
        validation_dataset,
        batch_size=batch_size,
        shuffle=False,
    )
    return tokenizer, train_loader, validation_loader
