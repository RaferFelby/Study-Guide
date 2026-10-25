"""有界SFT/DPO；冻结参考并检查有限梯度，不含续训接口。"""

import copy
import math

import torch

from data import batch_sequences, validate_pair
from objectives import dpo_loss, sequence_logps


def train_sft(model, prompts, completions, updates=120):
    if type(updates) is not int or not 1 <= updates <= 500:
        raise ValueError("SFT更新次数需为1～500")
    device = next(model.parameters()).device
    inputs, labels = batch_sequences(prompts, completions, device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.02, weight_decay=0)
    model.train()
    for _ in range(updates):
        optimizer.zero_grad(set_to_none=True)
        logps, counts = sequence_logps(model(inputs), labels)
        loss = -logps.sum() / counts.sum()
        if not torch.isfinite(loss):
            raise FloatingPointError("SFT损失非有限")
        loss.backward()
        norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        if not torch.isfinite(norm):
            raise FloatingPointError("SFT梯度非有限")
        optimizer.step()
    return float(loss.detach())


def make_reference(sft_model):
    reference = copy.deepcopy(sft_model).eval()
    reference.requires_grad_(False)
    reference.recurrent.flatten_parameters()
    return reference


def train_dpo(policy, reference, pairs, beta=0.1, updates=80, learning_rate=0.001):
    if type(updates) is not int or not 1 <= updates <= 500 or not pairs:
        raise ValueError("DPO更新次数需为1～500且数据非空")
    if (
        any(parameter.requires_grad for parameter in reference.parameters())
        or policy is reference
    ):
        raise ValueError("reference必须是独立且冻结的模型")
    for pair in pairs:
        validate_pair(pair)
    device = next(policy.parameters()).device
    prompts = [pair["prompt"] for pair in pairs]
    chosen_inputs, chosen_labels = batch_sequences(
        prompts, [pair["chosen"] for pair in pairs], device
    )
    rejected_inputs, rejected_labels = batch_sequences(
        prompts, [pair["rejected"] for pair in pairs], device
    )
    reference.eval()
    reference.recurrent.flatten_parameters()
    policy.recurrent.flatten_parameters()
    # 冻结参考与数据固定、无dropout，所以可预先缓存两侧log概率。
    with torch.no_grad():
        reference_chosen, _ = sequence_logps(reference(chosen_inputs), chosen_labels)
        reference_rejected, _ = sequence_logps(
            reference(rejected_inputs), rejected_labels
        )
    if (
        type(learning_rate) not in (int, float)
        or not math.isfinite(learning_rate)
        or not 0 < learning_rate <= 0.1
    ):
        raise ValueError("学习率需为(0,0.1]有限数")
    optimizer = torch.optim.AdamW(policy.parameters(), lr=learning_rate, weight_decay=0)
    policy.train()
    history = []
    for update in range(1, updates + 1):
        optimizer.zero_grad(set_to_none=True)
        policy_chosen, _ = sequence_logps(policy(chosen_inputs), chosen_labels)
        policy_rejected, _ = sequence_logps(policy(rejected_inputs), rejected_labels)
        loss, margin = dpo_loss(
            policy_chosen, policy_rejected, reference_chosen, reference_rejected, beta
        )
        loss.backward()
        norm = torch.nn.utils.clip_grad_norm_(policy.parameters(), 1.0)
        if not torch.isfinite(norm):
            raise FloatingPointError("DPO梯度非有限")
        optimizer.step()
        if update in {1, 20, 80, updates}:
            history.append(
                {
                    "update": update,
                    "loss_before_update": float(loss.detach()),
                    "mean_margin_before_update": float(margin.mean()),
                }
            )
    return history
