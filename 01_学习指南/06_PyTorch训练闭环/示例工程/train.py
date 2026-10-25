"""Command-line entry point for the Unit 06 training loop."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import torch
from app.data import build_loaders, make_dataset
from app.model import TinyRegressor
from app.training import (
    EarlyStopping,
    EpochRecord,
    evaluate,
    load_checkpoint,
    save_checkpoint,
    train_one_epoch,
    write_history,
)


def run(args: argparse.Namespace) -> list[EpochRecord]:
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dataset = make_dataset(size=160, seed=args.seed)
    train_loader, valid_loader = build_loaders(
        dataset,
        batch_size=args.batch_size,
        seed=args.seed,
        max_train_samples=12 if args.overfit_small else None,
    )
    model = TinyRegressor().to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.learning_rate,
        weight_decay=0.01,
    )
    scheduler = torch.optim.lr_scheduler.StepLR(
        optimizer,
        step_size=10,
        gamma=0.5,
    )
    early_stopping = EarlyStopping(patience=args.patience, min_delta=1e-5)
    scaler = torch.amp.GradScaler(
        device.type,
        enabled=args.amp and device.type == "cuda",
    )
    training_config: dict[str, int | float | bool | str] = {
        "seed": args.seed,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "clip_norm": args.clip_norm,
        "patience": args.patience,
        "amp": args.amp,
        "overfit_small": args.overfit_small,
        "inject_nan": args.inject_nan,
        "device": device.type,
    }
    output_dir = Path(args.output_dir)
    history: list[EpochRecord] = []
    start_epoch = 0
    if args.resume:
        checkpoint = load_checkpoint(
            Path(args.resume),
            model,
            optimizer,
            scheduler,
            early_stopping,
            scaler,
            device,
            training_config,
        )
        history = checkpoint["history"]
        start_epoch = checkpoint["epoch"] + 1

    for epoch in range(start_epoch, args.epochs):
        if device.type == "cuda":
            torch.cuda.reset_peak_memory_stats(device)
        train_metrics = train_one_epoch(
            model,
            train_loader,
            optimizer,
            device,
            scaler,
            clip_norm=args.clip_norm,
            use_amp=args.amp,
            inject_nan=args.inject_nan,
        )
        valid_metrics = evaluate(model, valid_loader, device)
        current: EpochRecord = {
            "epoch": epoch,
            "train_loss": train_metrics["loss"],
            "valid_loss": valid_metrics["loss"],
            "learning_rate": optimizer.param_groups[0]["lr"],
            "gradient_norm": train_metrics["gradient_norm"],
            "samples_per_second": train_metrics["samples_per_second"],
            "device": str(device),
            "cuda_memory_peak_bytes": (
                torch.cuda.max_memory_allocated(device)
                if device.type == "cuda"
                else None
            ),
        }
        history.append(current)
        is_best = (
            early_stopping.best is None
            or valid_metrics["loss"] < early_stopping.best - early_stopping.min_delta
        )
        should_stop = early_stopping.update(valid_metrics["loss"])
        scheduler.step()
        if is_best:
            save_checkpoint(
                output_dir / "best.pt",
                model,
                optimizer,
                scheduler,
                epoch,
                history,
                early_stopping,
                scaler,
                training_config,
            )
        save_checkpoint(
            output_dir / "last.pt",
            model,
            optimizer,
            scheduler,
            epoch,
            history,
            early_stopping,
            scaler,
            training_config,
        )
        write_history(output_dir / "history.json", history)
        if should_stop:
            break
    return history


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=0.01)
    parser.add_argument("--clip-norm", type=float, default=1.0)
    parser.add_argument("--patience", type=int, default=6)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--output-dir", default="results")
    parser.add_argument("--resume")
    parser.add_argument("--amp", action="store_true")
    parser.add_argument("--overfit-small", action="store_true")
    parser.add_argument("--inject-nan", action="store_true")
    args = parser.parse_args()
    if args.epochs < 1:
        parser.error("--epochs must be at least 1")
    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")
    if not math.isfinite(args.learning_rate) or args.learning_rate <= 0:
        parser.error("--learning-rate must be finite and positive")
    if not math.isfinite(args.clip_norm) or args.clip_norm <= 0:
        parser.error("--clip-norm must be finite and positive")
    if args.patience < 1:
        parser.error("--patience must be at least 1")
    return args


def main() -> None:
    run(parse_args())


if __name__ == "__main__":
    main()
