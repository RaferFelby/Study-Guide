import pytest
import torch
from torch import nn

from app.model import TransformerBlock
from block_parts_demo import add_residual, build_fixed_ffn, normalize_features


def test_embedding_lookup_and_repeated_id_gradient_accumulation():
    embedding = nn.Embedding(3, 2)
    with torch.no_grad():
        embedding.weight.copy_(torch.tensor([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]))
    features = embedding(torch.tensor([[2, 0, 2]], dtype=torch.long))
    torch.testing.assert_close(
        features, torch.tensor([[[1.0, 1.0], [1.0, 0.0], [1.0, 1.0]]])
    )
    features.sum().backward()
    torch.testing.assert_close(
        embedding.weight.grad, torch.tensor([[1.0, 1.0], [0.0, 0.0], [2.0, 2.0]])
    )


@pytest.mark.parametrize("token_id", [-1, 3])
def test_embedding_ids_are_not_python_negative_indices(token_id):
    with pytest.raises(IndexError):
        nn.Embedding(3, 2)(torch.tensor([token_id]))


def test_embedding_rejects_float_ids():
    with pytest.raises(RuntimeError):
        nn.Embedding(3, 2)(torch.tensor([1.0]))


def test_manual_layer_norm_matches_library_and_gradients():
    values = torch.tensor([[[1.0, 3.0], [10.0, 14.0]]], dtype=torch.float64)
    manual_input = values.clone().requires_grad_()
    reference_input = values.clone().requires_grad_()
    manual = normalize_features(manual_input)
    reference = nn.LayerNorm(2, elementwise_affine=False, dtype=torch.float64)(
        reference_input
    )
    torch.testing.assert_close(manual, reference)
    weights = torch.tensor([[[2.0, -1.0], [3.0, 4.0]]], dtype=torch.float64)
    (manual * weights).sum().backward()
    (reference * weights).sum().backward()
    torch.testing.assert_close(manual_input.grad, reference_input.grad)


def test_constant_features_are_finite_zero_before_affine_transform():
    values = torch.full((2, 3, 4), 7.0)
    torch.testing.assert_close(normalize_features(values), torch.zeros_like(values))


@pytest.mark.parametrize("dtype", [torch.float16, torch.bfloat16])
def test_teaching_implementation_rejects_untaught_low_precision(dtype):
    with pytest.raises(ValueError, match="float32"):
        normalize_features(torch.tensor([1.0, 3.0], dtype=dtype))


def test_finite_inputs_with_overflowing_statistics_are_rejected():
    with pytest.raises(ValueError, match="溢出"):
        normalize_features(torch.tensor([-1e30, 1e30]))


def test_epsilon_that_overflows_tensor_dtype_is_rejected():
    with pytest.raises(ValueError, match="溢出"):
        normalize_features(torch.tensor([1.0, 3.0]), eps=1e100)


@pytest.mark.parametrize("eps", [0.0, -1.0, float("nan"), float("inf")])
def test_manual_layer_norm_rejects_invalid_epsilon(eps):
    with pytest.raises(ValueError, match="eps"):
        normalize_features(torch.ones(2), eps)


@pytest.mark.parametrize(
    "values",
    [
        torch.tensor(1.0),
        torch.empty(2, 0),
        torch.tensor([1, 2]),
        torch.tensor([float("nan")]),
    ],
)
def test_manual_layer_norm_rejects_invalid_values(values):
    with pytest.raises(ValueError):
        normalize_features(values)


def test_ffn_has_fixed_hand_computable_result():
    network = build_fixed_ffn()
    values = torch.tensor([[[2.0, -1.0], [1.0, 3.0]]])
    torch.testing.assert_close(
        network(values), torch.tensor([[[5.0, -3.0], [1.0, 3.0]]])
    )


def test_ffn_and_layer_norm_do_not_mix_token_positions():
    values = torch.tensor([[[2.0, -1.0], [1.0, 3.0]]])
    changed = values.clone()
    changed[:, 1] = torch.tensor([99.0, 7.0])
    network = build_fixed_ffn()
    torch.testing.assert_close(network(values)[:, 0], network(changed)[:, 0])
    torch.testing.assert_close(
        normalize_features(values)[:, 0], normalize_features(changed)[:, 0]
    )


def test_layer_norm_affine_can_shift_mean_and_scale_variance():
    layer = nn.LayerNorm(2)
    with torch.no_grad():
        layer.weight.fill_(2)
        layer.bias.fill_(3)
    values = torch.tensor([[1.0, 3.0]])
    torch.testing.assert_close(layer(values), normalize_features(values) * 2 + 3)
    torch.testing.assert_close(layer(values).mean(), torch.tensor(3.0))


def test_residual_checks_shape_instead_of_allowing_broadcast():
    with pytest.raises(ValueError, match="形状"):
        add_residual(torch.ones(1, 2, 2), torch.ones(2))


def test_residual_identity_branch_contributes_to_gradient():
    values = torch.tensor([2.0], requires_grad=True)
    add_residual(values, 3 * values).sum().backward()
    torch.testing.assert_close(values.grad, torch.tensor([4.0]))


@pytest.mark.parametrize("norm_first", [True, False])
def test_zero_sublayers_expose_pre_and_post_norm_order(norm_first):
    block = TransformerBlock(2, 1, 3, dropout=0.0, norm_first=norm_first)
    with torch.no_grad():
        for parameter in block.attention.parameters():
            parameter.zero_()
        for parameter in block.feed_forward.parameters():
            parameter.zero_()
    values = torch.tensor([[[1.0, 3.0], [10.0, 14.0]]])
    block.eval()
    with torch.no_grad():
        result = block(values)
        expected = (
            values
            if norm_first
            else block.feed_forward_norm(block.attention_norm(values))
        )
    torch.testing.assert_close(result, expected)
    if not norm_first:
        assert not torch.allclose(result, values)
