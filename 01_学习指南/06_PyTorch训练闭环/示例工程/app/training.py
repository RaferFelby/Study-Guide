"""Training, validation, metrics and checkpoint helpers."""

from __future__ import annotations

import json
import math
from pathlib import Path
from time import perf_counter
from typing import Any, TypedDict

import torch
from torch import nn
from torch.utils.data import DataLoader


class EpochRecord(TypedDict):
    epoch: int
    train_loss: float
    valid_loss: float
    learning_rate: float
    gradient_norm: float
    samples_per_second: float
    device: str
    cuda_memory_peak_bytes: int | None


def check_batch(features: torch.Tensor, targets: torch.Tensor) -> None:
    if features.ndim != 2 or targets.ndim != 2:
        raise ValueError("features and targets must be two-dimensional")
    if features.shape[0] != targets.shape[0]:
        raise ValueError("features and targets must have equal batch size")
    if features.numel() == 0 or targets.numel() == 0:
        raise ValueError("batch tensors cannot be empty")
    if not torch.isfinite(features).all() or not torch.isfinite(targets).all():
        raise ValueError("batch contains NaN or infinite values")


def gradient_norm(model: nn.Module) -> float:
    squared_norm = 0.0
    for parameter in model.parameters():
        if parameter.grad is not None:
            squared_norm += float(parameter.grad.detach().norm(2).item() ** 2)
    return math.sqrt(squared_norm)


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    scaler: torch.amp.GradScaler,
    clip_norm: float | None = 1.0,
    use_amp: bool = False,
    inject_nan: bool = False,
) -> dict[str, float]:
    if clip_norm is not None and (not math.isfinite(clip_norm) or clip_norm <= 0):
        raise ValueError("clip_norm must be finite and positive")
    if len(loader) == 0:
        raise ValueError("training loader cannot be empty")
    model.train()
    loss_function = nn.MSELoss()
    total_loss = 0.0
    total_samples = 0
    total_elements = 0
    total_gradient_norm = 0.0
    started = perf_counter()

    for batch_index, (features, targets) in enumerate(loader):
        features = features.to(device)
        targets = targets.to(device)
        if inject_nan and batch_index == 0:
            features = features.clone()
            features[0, 0] = float("nan")
        try:
            check_batch(features, targets)
        except ValueError as error:
            raise ValueError(
                f"invalid training batch {batch_index}: {error}"
            ) from error
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast(
            device_type=device.type,
            enabled=use_amp and device.type == "cuda",
        ):
            predictions = model(features)
            if predictions.shape != targets.shape:
                raise ValueError(
                    f"prediction and target shapes differ at batch {batch_index}"
                )
            loss = loss_function(predictions, targets)
        if not torch.isfinite(loss):
            raise FloatingPointError(f"non-finite loss at batch {batch_index}")
        if scaler.is_enabled():
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
        else:
            loss.backward()
        before_clip = gradient_norm(model)
        if not math.isfinite(before_clip):
            raise FloatingPointError(f"non-finite gradient at batch {batch_index}")
        if clip_norm is not None:
            torch.nn.utils.clip_grad_norm_(model.parameters(), clip_norm)
        if scaler.is_enabled():
            scaler.step(optimizer)
            scaler.update()
        else:
            optimizer.step()
        batch_size = features.shape[0]
        # MSE 的 mean 按元素平均，多输出回归也要使用相同分母。
        total_loss += float(loss.detach().item()) * targets.numel()
        total_elements += targets.numel()
        total_samples += batch_size
        total_gradient_norm += before_clip

    elapsed = max(perf_counter() - started, 1e-9)
    return {
        "loss": total_loss / total_elements,
        "gradient_norm": total_gradient_norm / len(loader),
        "samples_per_second": total_samples / elapsed,
    }


@torch.no_grad()
def evaluate(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
) -> dict[str, float]:
    model.eval()
    loss_function = nn.MSELoss(reduction="sum")
    total_loss = 0.0
    total_elements = 0
    for features, targets in loader:
        features = features.to(device)
        targets = targets.to(device)
        check_batch(features, targets)
        predictions = model(features)
        if predictions.shape != targets.shape:
            raise ValueError("validation prediction and target shapes differ")
        loss = loss_function(predictions, targets)
        if not torch.isfinite(predictions).all() or not torch.isfinite(loss):
            raise FloatingPointError("non-finite validation output or loss")
        total_loss += float(loss.item())
        total_elements += targets.numel()
    if total_elements == 0:
        raise ValueError("validation loader cannot be empty")
    return {"loss": total_loss / total_elements}


class EarlyStopping:
    def __init__(self, patience: int = 5, min_delta: float = 0.0):
        if patience < 1:
            raise ValueError("patience must be positive")
        if not math.isfinite(min_delta) or min_delta < 0:
            raise ValueError("min_delta must be finite and non-negative")
        self.patience = patience
        self.min_delta = min_delta
        self.best: float | None = None
        self.bad_epochs = 0

    def update(self, metric: float) -> bool:
        if not math.isfinite(metric):
            raise ValueError("metric must be finite")
        if self.best is None or metric < self.best - self.min_delta:
            self.best = metric
            self.bad_epochs = 0
        else:
            self.bad_epochs += 1
        return self.bad_epochs >= self.patience

    def state_dict(self) -> dict[str, Any]:
        return {
            "patience": self.patience,
            "min_delta": self.min_delta,
            "best": self.best,
            "bad_epochs": self.bad_epochs,
        }

    def load_state_dict(self, state: dict[str, Any]) -> None:
        self.patience = state["patience"]
        self.min_delta = state["min_delta"]
        self.best = state["best"]
        self.bad_epochs = state["bad_epochs"]


def save_checkpoint(
    path: Path,
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    scheduler: torch.optim.lr_scheduler.LRScheduler,
    epoch: int,
    history: list[EpochRecord],
    early_stopping: EarlyStopping,
    scaler: torch.amp.GradScaler,
    training_config: dict[str, int | float | bool | str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "scheduler_state_dict": scheduler.state_dict(),
            "history": history,
            "early_stopping": early_stopping.state_dict(),
            "scaler_state_dict": scaler.state_dict(),
            "training_config": training_config,
            "torch_rng_state": torch.get_rng_state(),
            "cuda_rng_states": (
                torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None
            ),
        },
        path,
    )


def load_checkpoint(
    path: Path,
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    scheduler: torch.optim.lr_scheduler.LRScheduler,
    early_stopping: EarlyStopping,
    scaler: torch.amp.GradScaler,
    device: torch.device,
    training_config: dict[str, int | float | bool | str],
) -> dict[str, Any]:
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    if checkpoint["training_config"] != training_config:
        raise ValueError("resume settings differ from the saved training settings")
    model.load_state_dict(checkpoint["model_state_dict"])
    optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
    scheduler.load_state_dict(checkpoint["scheduler_state_dict"])
    early_stopping.load_state_dict(checkpoint["early_stopping"])
    scaler.load_state_dict(checkpoint["scaler_state_dict"])
    torch.set_rng_state(checkpoint["torch_rng_state"])
    if device.type == "cuda":
        cuda_rng_states = checkpoint["cuda_rng_states"]
        if cuda_rng_states is None or len(cuda_rng_states) != torch.cuda.device_count():
            raise ValueError("CUDA device count differs from the saved checkpoint")
        torch.cuda.set_rng_state_all(cuda_rng_states)
    return checkpoint


def write_history(path: Path, history: list[EpochRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, indent=2), encoding="utf-8")
