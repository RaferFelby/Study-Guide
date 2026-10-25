"""不跨样本看答案，也不训练跨样本下一个token。"""

import torch


def causal_mask(length, window=None, device="cpu"):
    if (
        type(length) is not int
        or length < 1
        or (window is not None and (type(window) is not int or window < 1))
    ):
        raise ValueError("长度和窗口需为正整数")
    positions = torch.arange(length, device=device)
    distance = positions[:, None] - positions[None, :]
    allowed = distance >= 0
    if window is not None:
        allowed &= distance < window
    return allowed


def pack_sequences(sequences):
    if not sequences or any(
        not sequence
        or any(type(token) is not int or not 1 <= token < 64 for token in sequence)
        for sequence in sequences
    ):
        raise ValueError("需为非空序列，token为1～63整数")
    tokens, labels, segments, positions = [], [], [], []
    for segment_id, sequence in enumerate(sequences):
        tokens.extend(sequence)
        labels.extend(sequence[1:] + [-100])
        segments.extend([segment_id] * len(sequence))
        positions.extend(range(len(sequence)))
    segment_tensor = torch.tensor(segments)
    allowed = (segment_tensor[:, None] == segment_tensor[None, :]) & causal_mask(
        len(tokens)
    )
    return {
        "tokens": torch.tensor([tokens]),
        "labels": torch.tensor([labels]),
        "positions": torch.tensor(positions),
        "allowed": allowed,
    }
