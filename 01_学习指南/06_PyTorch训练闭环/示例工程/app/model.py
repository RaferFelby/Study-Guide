"""Model definitions for the training example."""

from __future__ import annotations

import torch
from torch import nn


class TinyRegressor(nn.Module):
    def __init__(self, hidden_size: int = 16):
        super().__init__()
        if hidden_size < 1:
            raise ValueError("hidden_size must be positive")
        self.network = nn.Sequential(
            nn.Linear(1, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, 1),
        )

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        return self.network(features)


def parameter_summary(model: nn.Module) -> dict[str, int]:
    total = sum(parameter.numel() for parameter in model.parameters())
    trainable = sum(
        parameter.numel() for parameter in model.parameters() if parameter.requires_grad
    )
    return {"total": total, "trainable": trainable}
