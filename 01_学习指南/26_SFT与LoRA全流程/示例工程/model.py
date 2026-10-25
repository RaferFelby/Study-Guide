"""单块微型因果Transformer，手写LoRA展示冻结、低秩和合并。"""

import copy
import math

import torch
from torch import nn
from torch.nn import functional as F

from data import PAD_ID


class LoRALinear(nn.Module):
    def __init__(self, base, rank, alpha, dropout=0.0):
        super().__init__()
        if (
            type(rank) is not int
            or rank < 1
            or rank > min(base.in_features, base.out_features)
        ):
            raise ValueError("rank需为有效正整数")
        if not math.isfinite(alpha) or alpha <= 0 or not 0 <= dropout < 1:
            raise ValueError("alpha需有限正数，dropout范围[0,1)")
        self.base = base
        self.rank = rank
        self.scale = alpha / rank
        self.dropout = nn.Dropout(dropout)
        self.lora_a = nn.Parameter(
            torch.empty(
                rank,
                base.in_features,
                device=base.weight.device,
                dtype=base.weight.dtype,
            )
        )
        self.lora_b = nn.Parameter(
            torch.zeros(
                base.out_features,
                rank,
                device=base.weight.device,
                dtype=base.weight.dtype,
            )
        )
        nn.init.kaiming_uniform_(self.lora_a, a=math.sqrt(5))
        for parameter in base.parameters():
            parameter.requires_grad = False

    def forward(self, inputs):
        update = F.linear(F.linear(self.dropout(inputs), self.lora_a), self.lora_b)
        return self.base(inputs) + update * self.scale

    def merged(self):
        if self.training:
            raise RuntimeError("先eval再合并，dropout训练分支不等价")
        result = copy.deepcopy(self.base)
        with torch.no_grad():
            result.weight.add_((self.lora_b @ self.lora_a) * self.scale)
        return result


class TinyLM(nn.Module):
    def __init__(self, vocab_size, width=32, context_length=16):
        super().__init__()
        self.width = width
        self.context_length = context_length
        self.embedding = nn.Embedding(vocab_size, width, padding_idx=PAD_ID)
        self.position = nn.Embedding(context_length, width)
        self.norm_attention = nn.LayerNorm(width)
        self.q_proj = nn.Linear(width, width, bias=False)
        self.k_proj = nn.Linear(width, width, bias=False)
        self.v_proj = nn.Linear(width, width, bias=False)
        self.out_proj = nn.Linear(width, width, bias=False)
        self.norm_mlp = nn.LayerNorm(width)
        self.mlp = nn.Sequential(
            nn.Linear(width, width * 2), nn.GELU(), nn.Linear(width * 2, width)
        )
        self.norm_output = nn.LayerNorm(width)
        self.lm_head = nn.Linear(width, vocab_size, bias=False)

    def forward(self, inputs):
        if inputs.ndim != 2 or not 1 <= inputs.shape[1] <= self.context_length:
            raise ValueError("输入需为[batch,sequence]且不超上下文")
        positions = torch.arange(inputs.shape[1], device=inputs.device)
        hidden = self.embedding(inputs) + self.position(positions)
        normalized = self.norm_attention(hidden)
        query = self.q_proj(normalized).unsqueeze(1)
        key = self.k_proj(normalized).unsqueeze(1)
        value = self.v_proj(normalized).unsqueeze(1)
        attended = F.scaled_dot_product_attention(
            query, key, value, is_causal=True
        ).squeeze(1)
        hidden = hidden + self.out_proj(attended)
        hidden = hidden + self.mlp(self.norm_mlp(hidden))
        return self.lm_head(self.norm_output(hidden))


def add_lora(model, rank, targets=("q_proj", "v_proj", "lm_head"), dropout=0.0):
    if (
        not targets
        or len(set(targets)) != len(targets)
        or any(name not in {"q_proj", "v_proj", "lm_head"} for name in targets)
    ):
        raise ValueError("target modules需为不重复的已支持线性层")
    if any(isinstance(getattr(model, name), LoRALinear) for name in targets):
        raise ValueError("不要重复注入适配器")
    for parameter in model.parameters():
        parameter.requires_grad = False
    for name in targets:
        setattr(
            model,
            name,
            LoRALinear(getattr(model, name), rank, alpha=rank, dropout=dropout),
        )
    return model


def merge_lora(model):
    if model.training:
        raise RuntimeError("先eval再合并")
    result = copy.deepcopy(model)
    for name in ("q_proj", "v_proj", "lm_head"):
        layer = getattr(result, name)
        if isinstance(layer, LoRALinear):
            setattr(result, name, layer.merged())
    return result


def parameter_counts(model):
    return {
        "total": sum(parameter.numel() for parameter in model.parameters()),
        "trainable": sum(
            parameter.numel()
            for parameter in model.parameters()
            if parameter.requires_grad
        ),
    }
