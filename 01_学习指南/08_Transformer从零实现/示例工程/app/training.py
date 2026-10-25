"""运行小型语言模型的训练、验证与逐 token 生成。"""

from __future__ import annotations

import torch
from app.data import PAD_TOKEN_ID
from app.model import DecoderLanguageModel
from torch.nn import functional as F
from torch.utils.data import DataLoader


def next_token_loss(
    logits: torch.Tensor,
    target_ids: torch.Tensor,
    pad_token_id: int = PAD_TOKEN_ID,
) -> torch.Tensor:
    """计算 token 级交叉熵；padding 标签用 ignore_index 排除。"""
    if logits.ndim != 3 or target_ids.ndim != 2:
        raise ValueError("logits and target_ids must have shapes [B, T, V] and [B, T]")
    if logits.shape[:2] != target_ids.shape:
        raise ValueError(
            "logits and target_ids must have matching batch and sequence sizes"
        )
    if not logits.is_floating_point() or target_ids.dtype != torch.long:
        raise ValueError(
            "logits must be floating point and target_ids must be torch.long"
        )

    valid_targets = target_ids != pad_token_id
    if not valid_targets.any():
        raise ValueError("target_ids must contain at least one non-padding token")
    labels = target_ids.masked_fill(~valid_targets, -100)
    return F.cross_entropy(
        logits.reshape(-1, logits.shape[-1]),
        labels.reshape(-1),
        ignore_index=-100,
    )


def train_one_epoch(
    model: DecoderLanguageModel,
    data_loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
) -> float:
    """对训练数据完整遍历一次，返回按有效 token 加权的平均 loss。"""
    if len(data_loader) == 0:
        raise ValueError("training data_loader cannot be empty")
    model.train()
    total_loss = 0.0
    total_tokens = 0

    for input_ids, target_ids in data_loader:
        input_ids = input_ids.to(device)
        target_ids = target_ids.to(device)
        valid_tokens_mask = input_ids != PAD_TOKEN_ID

        optimizer.zero_grad(set_to_none=True)
        logits = model(input_ids, valid_tokens_mask=valid_tokens_mask)
        loss = next_token_loss(logits, target_ids)
        if not torch.isfinite(loss):
            raise FloatingPointError("training loss is not finite")
        loss.backward()
        optimizer.step()

        token_count = int((target_ids != PAD_TOKEN_ID).sum().item())
        total_loss += float(loss.detach().item()) * token_count
        total_tokens += token_count

    return total_loss / total_tokens


@torch.no_grad()
def evaluate_loss(
    model: DecoderLanguageModel,
    data_loader: DataLoader,
    device: torch.device,
) -> float:
    """在验证数据上计算 loss，不更新参数或记录梯度。"""
    if len(data_loader) == 0:
        raise ValueError("validation data_loader cannot be empty")
    model.eval()
    total_loss = 0.0
    total_tokens = 0

    for input_ids, target_ids in data_loader:
        input_ids = input_ids.to(device)
        target_ids = target_ids.to(device)
        logits = model(input_ids, valid_tokens_mask=input_ids != PAD_TOKEN_ID)
        loss = next_token_loss(logits, target_ids)
        token_count = int((target_ids != PAD_TOKEN_ID).sum().item())
        total_loss += float(loss.item()) * token_count
        total_tokens += token_count

    if total_tokens == 0:
        raise ValueError("validation data_loader contains no valid target tokens")
    return total_loss / total_tokens


@torch.no_grad()
def generate_token_ids(
    model: DecoderLanguageModel,
    prefix_ids: list[int],
    max_new_tokens: int,
    context_length: int,
    device: torch.device,
) -> list[int]:
    """每次读取当前前缀最后一个位置的 logits，贪心生成一个新 token。"""
    if not prefix_ids:
        raise ValueError("prefix_ids cannot be empty")
    if max_new_tokens < 0:
        raise ValueError("max_new_tokens cannot be negative")

    model.eval()
    generated_ids = torch.tensor(prefix_ids, dtype=torch.long, device=device)[None, :]
    for _ in range(max_new_tokens):
        model_input = generated_ids[:, -context_length:]
        logits = model(model_input)
        next_token_id = logits[:, -1, :].argmax(dim=-1, keepdim=True)
        generated_ids = torch.cat((generated_ids, next_token_id), dim=1)
    return generated_ids[0].tolist()
