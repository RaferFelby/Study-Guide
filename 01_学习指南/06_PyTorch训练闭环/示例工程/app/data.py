"""Deterministic synthetic data and DataLoader helpers."""

from __future__ import annotations

import torch
from torch.utils.data import DataLoader, Dataset, Subset, random_split


class RegressionDataset(Dataset):
    def __init__(self, features: torch.Tensor, targets: torch.Tensor):
        if len(features) != len(targets):
            raise ValueError("features and targets must have the same length")
        self.features = features.float()
        self.targets = targets.float()

    def __len__(self) -> int:
        return len(self.features)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        return self.features[index], self.targets[index]


def make_dataset(
    size: int = 160,
    noise: float = 0.05,
    seed: int = 7,
) -> RegressionDataset:
    if size < 2:
        raise ValueError("size must be at least 2")
    generator = torch.Generator().manual_seed(seed)
    features = torch.rand((size, 1), generator=generator) * 2 - 1
    targets = 2 * features.square() - 0.5 * features
    targets += noise * torch.randn((size, 1), generator=generator)
    return RegressionDataset(features, targets)


def build_loaders(
    dataset: Dataset,
    batch_size: int = 16,
    valid_ratio: float = 0.2,
    seed: int = 7,
    max_train_samples: int | None = None,
) -> tuple[DataLoader, DataLoader]:
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    if not 0 < valid_ratio < 1:
        raise ValueError("valid_ratio must be between zero and one")
    if max_train_samples is not None and max_train_samples < 1:
        raise ValueError("max_train_samples must be positive")
    valid_size = max(1, int(len(dataset) * valid_ratio))
    train_size = len(dataset) - valid_size
    if train_size < 1:
        raise ValueError("dataset is too small for the requested split")
    generator = torch.Generator().manual_seed(seed)
    train_set, valid_set = random_split(
        dataset,
        [train_size, valid_size],
        generator=generator,
    )
    if max_train_samples is not None:
        train_size = min(max_train_samples, len(train_set))
        train_set = Subset(train_set, range(train_size))
    train_loader = DataLoader(train_set, batch_size=batch_size, shuffle=True)
    valid_loader = DataLoader(valid_set, batch_size=batch_size, shuffle=False)
    return train_loader, valid_loader
