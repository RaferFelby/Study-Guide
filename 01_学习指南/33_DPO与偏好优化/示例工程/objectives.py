"""只对completion（含EOS）求序列log概率，再计算标准sigmoid DPO。"""

import math

import torch
from torch.nn import functional as F


def sequence_logps(logits, labels):
    if (
        logits.ndim != 3
        or labels.ndim != 2
        or logits.shape[:2] != labels.shape
        or logits.shape[1] < 2
    ):
        raise ValueError("logits需[B,T,V]，labels需[B,T]且长度至少2")
    shifted_labels = labels[:, 1:]
    mask = shifted_labels != -100
    if torch.any(mask.sum(dim=1) == 0):
        raise ValueError("每条回答必须有有效监督token")
    safe_labels = shifted_labels.masked_fill(~mask, 0)
    if torch.any(safe_labels < 0) or torch.any(safe_labels >= logits.shape[-1]):
        raise ValueError("标签超出词表")
    log_probs = F.log_softmax(logits[:, :-1].float(), dim=-1)
    token_logps = log_probs.gather(-1, safe_labels.unsqueeze(-1)).squeeze(-1)
    return (token_logps * mask).sum(dim=1), mask.sum(dim=1)


def dpo_loss(
    policy_chosen, policy_rejected, reference_chosen, reference_rejected, beta=0.1
):
    if type(beta) not in (int, float) or not math.isfinite(beta) or beta <= 0:
        raise ValueError("beta需为有限正数")
    values = (policy_chosen, policy_rejected, reference_chosen, reference_rejected)
    if (
        policy_chosen.ndim != 1
        or policy_chosen.numel() == 0
        or any(
            value.shape != policy_chosen.shape or not torch.isfinite(value).all()
            for value in values
        )
    ):
        raise ValueError("四组log概率需为同形非空有限向量")
    margin = beta * (
        (policy_chosen - policy_rejected)
        - (reference_chosen.detach() - reference_rejected.detach())
    )
    return -F.logsigmoid(margin).mean(), margin.detach()
