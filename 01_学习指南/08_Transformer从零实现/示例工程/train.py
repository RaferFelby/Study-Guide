"""训练一个字符级小型 decoder-only Transformer，并打印生成结果。"""

from __future__ import annotations

import argparse

import torch
from app.data import make_data_loaders
from app.model import DecoderLanguageModel
from app.training import evaluate_loss, generate_token_ids, train_one_epoch


def choose_device(requested_device: str) -> torch.device:
    """检查用户选择的设备；auto 优先使用可用 CUDA。"""
    if requested_device == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if requested_device == "cuda" and not torch.cuda.is_available():
        raise ValueError(
            "CUDA was requested, but this PyTorch environment has no CUDA device"
        )
    return torch.device(requested_device)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a tiny character-level Transformer"
    )
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--context-length", type=int, default=16)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    arguments = parser.parse_args()
    if arguments.epochs < 1:
        parser.error("--epochs must be positive")
    if arguments.batch_size < 1:
        parser.error("--batch-size must be positive")
    if arguments.context_length < 2:
        parser.error("--context-length must be at least 2")
    return arguments


def main() -> None:
    arguments = parse_arguments()
    torch.manual_seed(7)
    device = choose_device(arguments.device)
    tokenizer, train_loader, validation_loader = make_data_loaders(
        context_length=arguments.context_length,
        batch_size=arguments.batch_size,
    )
    model = DecoderLanguageModel(
        vocab_size=len(tokenizer.id_to_token),
        context_length=arguments.context_length,
        hidden_dim=32,
        num_heads=4,
        num_layers=2,
        feed_forward_dim=64,
        dropout=0.1,
        norm_first=True,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-3, weight_decay=0.01)

    print(f"PyTorch: {torch.__version__}")
    print(f"Device: {device}")
    if device.type == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(device)}")
    print(f"Vocabulary size: {len(tokenizer.id_to_token)}")
    print(f"Train windows: {len(train_loader.dataset)}")
    print(f"Validation windows: {len(validation_loader.dataset)}")

    initial_validation_loss = evaluate_loss(model, validation_loader, device)
    print(f"Initial validation loss: {initial_validation_loss:.3f}")
    for epoch in range(1, arguments.epochs + 1):
        training_loss = train_one_epoch(model, train_loader, optimizer, device)
        validation_loss = evaluate_loss(model, validation_loader, device)
        print(
            f"Epoch {epoch:02d}/{arguments.epochs:02d} "
            f"train_loss={training_loss:.3f} validation_loss={validation_loss:.3f}"
        )

    prefix_ids = tokenizer.encode("the ")
    generated_ids = generate_token_ids(
        model=model,
        prefix_ids=prefix_ids,
        max_new_tokens=48,
        context_length=arguments.context_length,
        device=device,
    )
    print(f"Generated text: {tokenizer.decode(generated_ids)}")


if __name__ == "__main__":
    main()
