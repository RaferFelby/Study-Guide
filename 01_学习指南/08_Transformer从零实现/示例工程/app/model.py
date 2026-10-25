"""从多头自注意力组装一个小型 decoder-only Transformer。"""

from __future__ import annotations

import torch
from app.attention import MultiHeadSelfAttention
from torch import nn


class TransformerBlock(nn.Module):
    """包含自注意力、残差连接、LayerNorm 和前馈网络的一个 Block。"""

    def __init__(
        self,
        hidden_dim: int,
        num_heads: int,
        feed_forward_dim: int,
        dropout: float = 0.0,
        norm_first: bool = True,
    ):
        super().__init__()
        if feed_forward_dim < 1:
            raise ValueError("feed_forward_dim must be positive")
        if not 0 <= dropout < 1:
            raise ValueError("dropout must be in the range [0, 1)")

        self.attention = MultiHeadSelfAttention(hidden_dim, num_heads)
        self.attention_norm = nn.LayerNorm(hidden_dim)
        self.feed_forward_norm = nn.LayerNorm(hidden_dim)
        self.feed_forward = nn.Sequential(
            nn.Linear(hidden_dim, feed_forward_dim),
            nn.GELU(),
            nn.Linear(feed_forward_dim, hidden_dim),
        )
        self.residual_dropout = nn.Dropout(dropout)
        self.norm_first = norm_first

    def forward(
        self,
        hidden_states: torch.Tensor,
        valid_tokens_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if self.norm_first:
            attention_input = self.attention_norm(hidden_states)
            attention_output = self.attention(
                attention_input, valid_tokens_mask=valid_tokens_mask
            )
            hidden_states = hidden_states + self.residual_dropout(attention_output)

            feed_forward_input = self.feed_forward_norm(hidden_states)
            feed_forward_output = self.feed_forward(feed_forward_input)
            return hidden_states + self.residual_dropout(feed_forward_output)

        attention_output = self.attention(
            hidden_states, valid_tokens_mask=valid_tokens_mask
        )
        hidden_states = self.attention_norm(
            hidden_states + self.residual_dropout(attention_output)
        )
        feed_forward_output = self.feed_forward(hidden_states)
        return self.feed_forward_norm(
            hidden_states + self.residual_dropout(feed_forward_output)
        )


class DecoderLanguageModel(nn.Module):
    """给定 token 序列，为每个位置预测下一个 token 的小模型。"""

    def __init__(
        self,
        vocab_size: int,
        context_length: int,
        hidden_dim: int = 32,
        num_heads: int = 4,
        num_layers: int = 2,
        feed_forward_dim: int = 64,
        dropout: float = 0.0,
        norm_first: bool = True,
    ):
        super().__init__()
        if vocab_size < 2 or context_length < 1 or num_layers < 1:
            raise ValueError("vocab_size, context_length, and num_layers are too small")

        self.context_length = context_length
        self.token_embedding = nn.Embedding(vocab_size, hidden_dim)
        self.blocks = nn.ModuleList(
            [
                TransformerBlock(
                    hidden_dim=hidden_dim,
                    num_heads=num_heads,
                    feed_forward_dim=feed_forward_dim,
                    dropout=dropout,
                    norm_first=norm_first,
                )
                for _ in range(num_layers)
            ]
        )
        self.final_norm = nn.LayerNorm(hidden_dim)
        self.language_model_head = nn.Linear(hidden_dim, vocab_size, bias=False)

    def forward(
        self,
        input_ids: torch.Tensor,
        valid_tokens_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if input_ids.ndim != 2:
            raise ValueError("input_ids must have shape [batch, sequence]")
        if input_ids.shape[1] < 1 or input_ids.shape[1] > self.context_length:
            raise ValueError("sequence length must be within the model context length")

        hidden_states = self.token_embedding(input_ids)
        for block in self.blocks:
            hidden_states = block(hidden_states, valid_tokens_mask=valid_tokens_mask)
        hidden_states = self.final_norm(hidden_states)
        return self.language_model_head(hidden_states)
