"""小型因果Decoder：朴素注意力、SDPA与按层激活重算。"""

import math

import torch
from torch import nn
from torch.nn import functional as F
from torch.utils.checkpoint import checkpoint

from packing import causal_mask
from position import apply_rope

VOCAB_SIZE, WIDTH, HEADS, LAYERS = 64, 64, 4, 4


class DecoderBlock(nn.Module):
    def __init__(self, attention="eager"):
        super().__init__()
        self.attention = attention
        self.norm_attention = nn.LayerNorm(WIDTH)
        self.query_key_value = nn.Linear(WIDTH, WIDTH * 3)
        self.output = nn.Linear(WIDTH, WIDTH)
        self.norm_feedforward = nn.LayerNorm(WIDTH)
        self.feedforward = nn.Sequential(
            nn.Linear(WIDTH, WIDTH * 4), nn.GELU(), nn.Linear(WIDTH * 4, WIDTH)
        )

    def forward(self, hidden, positions, allowed):
        batch_size, length, _ = hidden.shape
        projected = self.query_key_value(self.norm_attention(hidden))
        query, key, value = projected.chunk(3, dim=-1)
        head_dim = WIDTH // HEADS
        query = query.reshape(batch_size, length, HEADS, head_dim).transpose(1, 2)
        key = key.reshape(batch_size, length, HEADS, head_dim).transpose(1, 2)
        value = value.reshape(batch_size, length, HEADS, head_dim).transpose(1, 2)
        query, key = apply_rope(query, positions), apply_rope(key, positions)
        if self.attention == "eager":
            allowed = (
                causal_mask(length, device=hidden.device)
                if allowed is None
                else allowed
            )
            scores = query @ key.transpose(-2, -1) / math.sqrt(head_dim)
            scores = scores.masked_fill(~allowed, float("-inf"))
            probabilities = scores.float().softmax(-1).to(value.dtype)
            attended = probabilities @ value
        else:
            attended = F.scaled_dot_product_attention(
                query,
                key,
                value,
                attn_mask=allowed,
                dropout_p=0.0,
                is_causal=allowed is None,
            )
        attended = (
            attended.transpose(1, 2).contiguous().reshape(batch_size, length, WIDTH)
        )
        hidden = hidden + self.output(attended)
        return hidden + self.feedforward(self.norm_feedforward(hidden))


class TinyDecoder(nn.Module):
    def __init__(self, attention="eager", checkpoint_layers=False):
        super().__init__()
        if attention not in {"eager", "sdpa"}:
            raise ValueError("attention需为eager或sdpa")
        self.checkpoint_layers = checkpoint_layers
        self.embedding = nn.Embedding(VOCAB_SIZE, WIDTH)
        self.blocks = nn.ModuleList([DecoderBlock(attention) for _ in range(LAYERS)])
        self.output = nn.Linear(WIDTH, VOCAB_SIZE)

    def forward(self, tokens, positions=None, allowed=None):
        length = tokens.shape[1]
        positions = (
            torch.arange(length, device=tokens.device)
            if positions is None
            else positions
        )
        hidden = self.embedding(tokens)
        for block in self.blocks:
            if self.checkpoint_layers and self.training:
                hidden = checkpoint(
                    block, hidden, positions, allowed, use_reentrant=False
                )
            else:
                hidden = block(hidden, positions, allowed)
        return self.output(hidden)
