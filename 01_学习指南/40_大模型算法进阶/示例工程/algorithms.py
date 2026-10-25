"""小规模机制实验；不下载权重，不把合成任务当作语言模型训练收益。"""

import math

import torch


def clipped_surrogate(
    ratios: torch.Tensor, advantages: torch.Tensor, epsilon: float = 0.2
):
    if ratios.shape != advantages.shape or ratios.numel() == 0:
        raise ValueError("ratios and advantages need equal non-empty shapes")
    if not 0 < epsilon < 1:
        raise ValueError("epsilon must be in (0, 1)")
    if (
        not torch.isfinite(ratios).all()
        or not torch.isfinite(advantages).all()
        or (ratios <= 0).any()
    ):
        raise ValueError("ratios must be finite and positive; advantages finite")
    return torch.minimum(
        ratios * advantages, ratios.clamp(1 - epsilon, 1 + epsilon) * advantages
    )


def group_advantages(rewards: torch.Tensor) -> torch.Tensor:
    if rewards.ndim != 2 or rewards.shape[1] < 2 or rewards.numel() == 0:
        raise ValueError("rewards must be groups by at least two candidates")
    if not rewards.is_floating_point() or not torch.isfinite(rewards).all():
        raise ValueError("rewards must be finite floating values")
    centered = rewards - rewards.mean(dim=1, keepdim=True)
    deviation = rewards.std(dim=1, keepdim=True, unbiased=False)
    return centered / deviation.clamp_min(1e-8)


def train_bandit(method: str, seed: int = 2026) -> dict:
    """一步、两动作任务：动作 1 得 1 分；动作 0 得 0 分。"""
    if method not in {"ppo", "grpo"}:
        raise ValueError("method must be ppo or grpo")
    generator = torch.Generator().manual_seed(seed)
    logits = torch.nn.Parameter(torch.zeros(2, dtype=torch.float64))
    value = torch.nn.Parameter(torch.zeros((), dtype=torch.float64))
    parameters = [logits, value] if method == "ppo" else [logits]
    optimizer = torch.optim.Adam(parameters, lr=0.05)
    reference = torch.tensor([0.5, 0.5], dtype=torch.float64)
    history = []
    for iteration in range(20):
        with torch.no_grad():
            old_log_probs = logits.log_softmax(dim=0).clone()
            actions = torch.multinomial(
                old_log_probs.exp(), 64, replacement=True, generator=generator
            )
            rewards = actions.to(torch.float64)
            if method == "ppo":
                advantages = rewards - value.detach()
            else:
                advantages = group_advantages(rewards.reshape(16, 4)).reshape(-1)
        for _ in range(4):
            optimizer.zero_grad()
            log_probs = logits.log_softmax(dim=0)
            ratios = (log_probs[actions] - old_log_probs[actions]).exp()
            policy_loss = -clipped_surrogate(ratios, advantages).mean()
            # 两动作可以精确求 KL；这不是原论文的 token 采样 KL 估计器。
            kl = (log_probs.exp() * (log_probs - reference.log())).sum()
            loss = policy_loss + 0.02 * kl
            if method == "ppo":
                loss = loss + 0.5 * (value - rewards).square().mean()
            if not torch.isfinite(loss):
                raise ValueError("non-finite training loss")
            loss.backward()
            if any(
                parameter.grad is None or not torch.isfinite(parameter.grad).all()
                for parameter in parameters
            ):
                raise ValueError("non-finite or missing gradient")
            optimizer.step()
        history.append(
            {
                "iteration": iteration,
                "sample_reward": rewards.mean().item(),
                "probability_action_1": logits.softmax(dim=0)[1].item(),
            }
        )
    return {
        "method": method,
        "scope": "one_step_two_action_bandit",
        "seed": seed,
        "initial_probability": 0.5,
        "final_probability": history[-1]["probability_action_1"],
        "history": history,
    }


def route_experts(scores: torch.Tensor, expert_outputs: torch.Tensor, top_k: int):
    """scores: token×expert；expert_outputs: token×expert×feature。"""
    if (
        scores.ndim != 2
        or expert_outputs.ndim != 3
        or expert_outputs.shape[:2] != scores.shape
    ):
        raise ValueError("expected scores [T,E] and outputs [T,E,D]")
    if (
        scores.numel() == 0
        or expert_outputs.shape[-1] == 0
        or type(top_k) is not int
        or not 1 <= top_k <= scores.shape[1]
    ):
        raise ValueError("invalid size or top_k")
    if not torch.isfinite(scores).all() or not torch.isfinite(expert_outputs).all():
        raise ValueError("finite scores and outputs required")
    selected_scores, indices = scores.topk(top_k, dim=1)
    weights = selected_scores.softmax(dim=1)
    outputs = []
    for token_index in range(scores.shape[0]):
        selected = expert_outputs[token_index, indices[token_index]]
        outputs.append((weights[token_index, :, None] * selected).sum(dim=0))
    return torch.stack(outputs), indices, weights


def latent_attention_example() -> dict:
    query = torch.tensor([[1.0, 0.0]], dtype=torch.float64)
    latent = torch.tensor([[1.0], [2.0], [3.0]], dtype=torch.float64)
    key_projection = torch.tensor([[1.0, 2.0]], dtype=torch.float64)
    value_projection = torch.tensor([[2.0, -1.0]], dtype=torch.float64)
    keys = latent @ key_projection
    values = latent @ value_projection
    weights = (query @ keys.T / math.sqrt(2)).softmax(dim=-1)
    reconstructed = weights @ values
    compressed_scores = (query @ key_projection.T) @ latent.T / math.sqrt(2)
    compressed = (compressed_scores.softmax(dim=-1) @ latent) @ value_projection
    return {
        "reconstructed": reconstructed.tolist(),
        "compressed": compressed.tolist(),
        "max_error": (reconstructed - compressed).abs().max().item(),
        "kv_elements": keys.numel() + values.numel(),
        "latent_elements": latent.numel(),
    }


def uniform_quantize(weights: torch.Tensor):
    if (
        weights.numel() == 0
        or not weights.is_floating_point()
        or not torch.isfinite(weights).all()
    ):
        raise ValueError("weights must be non-empty finite floating values")
    maximum = weights.abs().max()
    scale = maximum / 7 if maximum > 0 else weights.new_tensor(1.0)
    codes = (weights / scale).round().clamp(-7, 7).to(torch.int8)
    restored = codes.to(weights.dtype) * scale
    return codes, scale, restored


def quantized_adapter_example() -> dict:
    weights = torch.tensor([[0.1, 0.4], [0.7, -1.0]], dtype=torch.float64)
    codes, scale, base = uniform_quantize(weights)
    base = base.detach()
    adapter_a = torch.nn.Parameter(torch.tensor([[0.2], [0.1]], dtype=torch.float64))
    adapter_b = torch.nn.Parameter(torch.zeros((1, 2), dtype=torch.float64))
    inputs = torch.eye(2, dtype=torch.float64)
    # 构造一个秩为 1 的任务变化，便于隔离适配器机制。
    target = inputs @ (
        base + torch.tensor([[0.2, -0.2], [0.1, -0.1]], dtype=torch.float64)
    )
    optimizer = torch.optim.Adam([adapter_a, adapter_b], lr=0.03)
    before = ((inputs @ base - target) ** 2).mean().item()
    original = base.clone()
    for _ in range(80):
        optimizer.zero_grad()
        prediction = inputs @ base + (inputs @ adapter_a) @ adapter_b
        loss = (prediction - target).square().mean()
        loss.backward()
        optimizer.step()
    after = (
        ((inputs @ base + (inputs @ adapter_a) @ adapter_b - target) ** 2).mean().item()
    )
    return {
        "scope": "uniform_quantization_and_adapter_not_full_qlora",
        "codes": codes.tolist(),
        "scale": scale.item(),
        "before": before,
        "after": after,
        "base_unchanged": torch.equal(base, original),
        "base_has_gradient": base.grad is not None,
    }
