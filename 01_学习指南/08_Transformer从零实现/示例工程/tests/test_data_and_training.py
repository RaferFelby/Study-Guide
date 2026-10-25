import pytest
import torch
from app.data import NextTokenDataset, make_data_loaders
from app.model import DecoderLanguageModel
from app.training import evaluate_loss, next_token_loss, train_one_epoch


def test_next_token_dataset_shifts_targets_by_one_position() -> None:
    dataset = NextTokenDataset([3, 4, 5, 6, 7], context_length=3)

    input_ids, target_ids = dataset[0]

    assert input_ids.tolist() == [3, 4, 5]
    assert target_ids.tolist() == [4, 5, 6]
    assert len(dataset) == 2


def test_padding_targets_are_ignored_in_loss() -> None:
    logits = torch.tensor([[[4.0, 0.0], [0.0, 4.0]]])
    target_ids = torch.tensor([[1, 0]])

    loss_with_padding = next_token_loss(logits, target_ids)
    loss_without_padding = torch.nn.functional.cross_entropy(
        logits[:, :1, :].reshape(-1, 2), target_ids[:, :1].reshape(-1)
    )

    torch.testing.assert_close(loss_with_padding, loss_without_padding)


def test_data_loader_rejects_unknown_validation_character() -> None:
    tokenizer, _, _ = make_data_loaders(context_length=8, batch_size=4)

    with pytest.raises(ValueError, match="outside the vocabulary"):
        tokenizer.encode("?")


def test_training_epoch_runs_on_cpu_and_validation_is_finite() -> None:
    tokenizer, train_loader, validation_loader = make_data_loaders(
        context_length=8, batch_size=16
    )
    model = DecoderLanguageModel(
        vocab_size=len(tokenizer.id_to_token),
        context_length=8,
        hidden_dim=16,
        num_heads=4,
        num_layers=1,
        feed_forward_dim=32,
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    initial_loss = evaluate_loss(model, validation_loader, torch.device("cpu"))
    training_loss = train_one_epoch(model, train_loader, optimizer, torch.device("cpu"))
    final_loss = evaluate_loss(model, validation_loader, torch.device("cpu"))

    assert torch.isfinite(torch.tensor(training_loss))
    assert torch.isfinite(torch.tensor(initial_loss))
    assert torch.isfinite(torch.tensor(final_loss))
