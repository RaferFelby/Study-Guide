import ctypes

import pytest
import torch

from operator_impl import affine, load_function


@pytest.mark.parametrize("device", ["cpu", "cuda"])
@pytest.mark.parametrize("shape", [(0,), (), (1,), (257,), (2, 3)])
def test_values_and_gradient(device, shape):
    value = torch.arange(
        torch.tensor(shape).prod().item() if shape else 1,
        device=device,
        dtype=torch.float32,
    ).reshape(shape)
    value.requires_grad_()
    actual = affine(value, 2.0, -1.0)
    torch.testing.assert_close(actual, value * 2 - 1)
    actual.sum().backward()
    torch.testing.assert_close(value.grad, torch.full_like(value, 2.0))
    assert actual.data_ptr() != value.data_ptr() or value.numel() == 0


@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_registration(device):
    value = torch.ones(3, device=device, requires_grad=True)
    torch.library.opcheck(affine, (value, 2.0, 1.0))


@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_bad_layout(device):
    with pytest.raises(ValueError, match="连续"):
        affine(torch.ones(2, 3, device=device).T, 2.0, 1.0)


@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_bad_dtype(device):
    with pytest.raises(ValueError, match="float32"):
        affine(torch.ones(3, device=device, dtype=torch.float64), 2.0, 1.0)


@pytest.mark.parametrize("bad", [float("inf"), float("nan"), 1e100])
def test_bad_scalar(bad):
    with pytest.raises(ValueError, match="有限"):
        affine(torch.ones(3), bad, 1.0)


def test_c_boundary_without_dereferencing_invalid_memory():
    function = load_function("cpu")
    assert function(None, None, -1, 2, 1) == -1
    assert function(None, None, 1, 2, 1) == -1
    assert function(None, None, 0, 2, 1) == 0
    assert ctypes.sizeof(ctypes.c_float) == 4


def test_non_default_cuda_stream():
    stream = torch.cuda.Stream()
    with torch.cuda.stream(stream):
        value = torch.arange(257, device="cuda", dtype=torch.float32)
        result = affine(value, 2.0, 1.0)
        expected = value * 2 + 1
    stream.synchronize()
    torch.testing.assert_close(result, expected)


@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_fractional_values_and_finite_difference(device):
    value = torch.tensor([-0.7, 0.2, 1.3], device=device)
    scale, bias, step = -1.25, 0.7, 0.001
    actual = affine(value, scale, bias)
    torch.testing.assert_close(actual, value * scale + bias)
    difference = (
        affine(value + step, scale, bias) - affine(value - step, scale, bias)
    ) / (2 * step)
    torch.testing.assert_close(
        difference, torch.full_like(value, scale), rtol=0.001, atol=0.001
    )


def test_missing_library_has_clear_message(tmp_path, monkeypatch):
    import operator_impl

    monkeypatch.setattr(operator_impl, "ROOT", tmp_path)
    monkeypatch.setattr(operator_impl, "LIBRARIES", {})
    with pytest.raises(RuntimeError, match="先运行 build.py"):
        operator_impl.load_function("cpu")


def test_negative_view_requires_resolution():
    from operator_impl import check_input

    # 私有构造器只用于边界回归；公开求值由 PyTorch 分发器处理负号视图。
    value = torch._neg_view(torch.ones(3))
    with pytest.raises(ValueError, match="负号视图"):
        check_input(value, 2.0, 1.0)
    torch.testing.assert_close(affine(value, 2.0, 1.0), torch.full_like(value, -1.0))
    torch.testing.assert_close(
        affine(value.resolve_neg(), 2.0, 1.0), torch.full_like(value, -1.0)
    )
