"""变长整数序列的右侧填充，供数据加载补充课使用。"""

from __future__ import annotations

import torch


def collate_integer_sequences(
    sequences: list[list[int]],
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """返回 CPU 上的填充值、原始长度和 True 表示有效位置的布尔掩码。"""
    if not sequences:
        raise ValueError("batch must contain at least one sequence")
    lengths_list = []
    for sequence in sequences:
        if not isinstance(sequence, list):
            raise TypeError("each sequence must be a list")
        for value in sequence:
            if type(value) is not int or not -(2**63) <= value < 2**63:
                raise ValueError("sequence values must be signed 64-bit integers")
        lengths_list.append(len(sequence))

    batch_size = len(sequences)
    max_length = max(lengths_list)
    padded_values = torch.zeros((batch_size, max_length), dtype=torch.long)
    mask = torch.zeros((batch_size, max_length), dtype=torch.bool)
    for row, sequence in enumerate(sequences):
        length = lengths_list[row]
        if length > 0:
            padded_values[row, :length] = torch.tensor(sequence, dtype=torch.long)
            mask[row, :length] = True
    lengths = torch.tensor(lengths_list, dtype=torch.long)
    return padded_values, lengths, mask
