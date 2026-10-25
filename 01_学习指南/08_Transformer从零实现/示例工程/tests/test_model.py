import pytest
import torch
from app.model import DecoderLanguageModel, TransformerBlock

DEVICES = ["cpu"]
if torch.cuda.is_available():
    DEVICES.append("cuda")


@pytest.mark.parametrize("device", DEVICES)
@pytest.mark.parametrize("norm_first", [True, False])
def test_decoder_model_shape_and_gradients(device: str, norm_first: bool) -> None:
    model = DecoderLanguageModel(
        vocab_size=12,
        context_length=8,
        hidden_dim=16,
        num_heads=4,
        num_layers=2,
        feed_forward_dim=32,
        norm_first=norm_first,
    ).to(device)
    input_ids = torch.randint(1, 12, (2, 6), device=device)

    logits = model(input_ids)
    logits.square().mean().backward()

    assert logits.shape == (2, 6, 12)
    assert all(
        parameter.grad is not None and torch.isfinite(parameter.grad).all()
        for parameter in model.parameters()
    )


def test_causal_decoder_logits_do_not_depend_on_future_tokens() -> None:
    torch.manual_seed(2)
    model = DecoderLanguageModel(
        vocab_size=10,
        context_length=6,
        hidden_dim=16,
        num_heads=4,
        num_layers=2,
        feed_forward_dim=32,
    )
    model.eval()
    first_sequence = torch.tensor([[1, 2, 3, 4, 5]])
    changed_future = torch.tensor([[1, 2, 3, 4, 8]])

    first_logits = model(first_sequence)
    changed_logits = model(changed_future)

    torch.testing.assert_close(first_logits[:, :4], changed_logits[:, :4])


def test_transformer_block_rejects_invalid_dropout() -> None:
    with pytest.raises(ValueError, match="dropout"):
        TransformerBlock(
            hidden_dim=16,
            num_heads=4,
            feed_forward_dim=32,
            dropout=1.0,
        )
