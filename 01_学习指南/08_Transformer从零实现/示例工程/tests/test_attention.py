import pytest
import torch
from app.attention import (
    MultiHeadSelfAttention,
    apply_rotary_position_embedding,
    scaled_dot_product_attention,
)

DEVICES = ["cpu"]
if torch.cuda.is_available():
    DEVICES.append("cuda")


@pytest.mark.parametrize("device", DEVICES)
def test_attention_returns_input_shape_and_finite_gradients(device: str) -> None:
    query = torch.randn(2, 2, 5, 4, device=device, requires_grad=True)
    key = torch.randn(2, 2, 5, 4, device=device, requires_grad=True)
    value = torch.randn(2, 2, 5, 4, device=device, requires_grad=True)

    context = scaled_dot_product_attention(query, key, value)
    context.square().mean().backward()

    assert context.shape == value.shape
    assert torch.isfinite(context).all()
    assert query.grad is not None and torch.isfinite(query.grad).all()
    assert key.grad is not None and torch.isfinite(key.grad).all()
    assert value.grad is not None and torch.isfinite(value.grad).all()


@pytest.mark.parametrize("device", DEVICES)
def test_causal_attention_does_not_read_future_keys_or_values(device: str) -> None:
    query = torch.ones(1, 1, 4, 2, device=device)
    key = torch.zeros_like(query)
    value = torch.arange(8, dtype=torch.float32, device=device).view(1, 1, 4, 2)
    changed_key = key.clone()
    changed_value = value.clone()
    changed_key[:, :, 3, :] = 100
    changed_value[:, :, 3, :] = -100

    original_context = scaled_dot_product_attention(query, key, value)
    changed_context = scaled_dot_product_attention(query, changed_key, changed_value)

    torch.testing.assert_close(original_context[:, :, :3], changed_context[:, :, :3])


@pytest.mark.parametrize("device", DEVICES)
def test_padding_mask_excludes_invalid_keys(device: str) -> None:
    query = torch.ones(1, 1, 3, 2, device=device)
    key = torch.zeros_like(query)
    value = (
        torch.tensor([1.0, 2.0, 900.0], device=device)
        .view(1, 1, 3, 1)
        .expand(-1, -1, -1, 2)
    )
    valid_tokens_mask = torch.tensor([[True, True, False]], device=device)
    changed_value = value.clone()
    changed_value[:, :, 2, :] = -900

    context = scaled_dot_product_attention(
        query, key, value, is_causal=False, valid_tokens_mask=valid_tokens_mask
    )
    changed_context = scaled_dot_product_attention(
        query, key, changed_value, is_causal=False, valid_tokens_mask=valid_tokens_mask
    )

    torch.testing.assert_close(context, changed_context)


def test_rotary_position_zero_keeps_values_unchanged() -> None:
    tensor = torch.randn(2, 3, 4, 8)

    transformed = apply_rotary_position_embedding(tensor)

    torch.testing.assert_close(transformed[:, :, 0, :], tensor[:, :, 0, :])
    assert transformed.shape == tensor.shape


def test_attention_rejects_invalid_head_dimension_or_mask() -> None:
    with pytest.raises(ValueError, match="even"):
        MultiHeadSelfAttention(hidden_dim=15, num_heads=3)

    query = torch.randn(1, 1, 3, 2)
    with pytest.raises(ValueError, match="shape"):
        scaled_dot_product_attention(
            query,
            query,
            query,
            valid_tokens_mask=torch.ones(1, 2, dtype=torch.bool),
        )


def test_causal_attention_rejects_left_padding() -> None:
    query = torch.randn(1, 1, 3, 2)
    left_padded_mask = torch.tensor([[False, True, True]])

    with pytest.raises(ValueError, match="right padding"):
        scaled_dot_product_attention(
            query, query, query, valid_tokens_mask=left_padded_mask
        )
