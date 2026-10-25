"""只监督模型计划/动作/答案/拒答，不监督环境观察。"""

import torch
from torch.nn import functional as F

from data import batch_rows


def train_model(model, rows, updates=200):
    if type(updates) is not int or not 1 <= updates <= 500:
        raise ValueError("更新次数需为1～500整数")
    inputs, labels = batch_rows(rows, next(model.parameters()).device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.01, weight_decay=0)
    model.recurrent.flatten_parameters()
    model.train()
    losses = []
    for update in range(1, updates + 1):
        optimizer.zero_grad(set_to_none=True)
        logits = model(inputs)[:, :-1]
        shifted = labels[:, 1:]
        loss = F.cross_entropy(
            logits.reshape(-1, logits.shape[-1]), shifted.reshape(-1), ignore_index=-100
        )
        if not torch.isfinite(loss):
            raise FloatingPointError("训练损失非有限")
        loss.backward()
        norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        if not torch.isfinite(norm):
            raise FloatingPointError("梯度非有限")
        optimizer.step()
        if update in {1, 50, updates}:
            losses.append(
                {"update": update, "loss_before_update": float(loss.detach())}
            )
    return losses
