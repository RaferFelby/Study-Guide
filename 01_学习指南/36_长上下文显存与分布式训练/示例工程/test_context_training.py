"""因果、样本边界、梯度一致与本机DDP的行为验证。"""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
import torch
from torch.nn import functional as F
from torch.nn.attention import SDPBackend

from experiment import run, run_step
from model import TinyDecoder
from packing import causal_mask, pack_sequences
from packing_experiment import padded_batch
from planning import attention_matrix_bytes, memory_plan, training_state_bytes
from position import apply_rope, rope_angles


def test_quadratic_attention_and_state_sharding_estimate():
    assert attention_matrix_bytes(2, 4, 128) == 524288
    assert attention_matrix_bytes(2, 4, 256) == 4 * attention_matrix_bytes(2, 4, 128)
    assert [
        training_state_bytes(100, 4, name)
        for name in ("ddp", "zero1", "zero2", "zero3")
    ] == [1600, 1000, 700, 400]
    assert not memory_plan(7_000_000_000, 8, 1)["estimated_fits"]


@pytest.mark.parametrize("args", [(0, 1, 1), (1, 1, -1), (True, 1, 1)])
def test_bad_attention_shape_fails(args):
    with pytest.raises(ValueError):
        attention_matrix_bytes(*args)


def test_bad_strategy_and_capacity_fail():
    with pytest.raises(ValueError):
        training_state_bytes(100, 2, "magic")
    with pytest.raises(ValueError):
        memory_plan(100, 0, 1)


@pytest.mark.parametrize("capacity", [float("nan"), float("inf")])
def test_nonfinite_capacity_fails(capacity):
    with pytest.raises(ValueError):
        memory_plan(100, capacity, 1)


def test_causal_and_window_masks():
    mask = causal_mask(5)
    assert mask[4, 0] and not mask[0, 4]
    window = causal_mask(5, 2)
    assert window[4, 3] and window[4, 4] and not window[4, 2]
    with pytest.raises(ValueError):
        causal_mask(5, 0)


def test_packing_resets_positions_and_masks_boundaries():
    packed = pack_sequences([[1, 2, 3], [4, 5]])
    assert packed["positions"].tolist() == [0, 1, 2, 0, 1]
    assert packed["labels"].tolist() == [[2, 3, -100, 5, -100]]
    assert not packed["allowed"][3, 2]
    assert packed["allowed"][4, 3] and not packed["allowed"][3, 4]


@pytest.mark.parametrize("sequences", [[], [[]], [[0]], [[64]], [[True]]])
def test_invalid_sequences_fail(sequences):
    with pytest.raises(ValueError):
        pack_sequences(sequences)


def test_rope_preserves_norm_and_zero_position():
    torch.manual_seed(2)
    states = torch.randn(2, 4, 5, 16)
    rotated = apply_rope(states, torch.arange(5))
    torch.testing.assert_close(rotated.norm(dim=-1), states.norm(dim=-1))
    torch.testing.assert_close(rotated[..., 0, :], states[..., 0, :])
    torch.testing.assert_close(
        rope_angles(torch.tensor([4096]), 16, 2), rope_angles(torch.tensor([2048]), 16)
    )


@pytest.mark.parametrize("dimension,scale", [(3, 1), (16, 0.5), (16, float("inf"))])
def test_invalid_rope_configuration_fails(dimension, scale):
    with pytest.raises(ValueError):
        rope_angles(torch.arange(5), dimension, scale)


def test_model_cannot_see_future_tokens():
    torch.set_num_threads(2)
    model = TinyDecoder().eval()
    original = torch.tensor([[1, 2, 3, 4]])
    changed = original.clone()
    changed[0, -1] = 5
    with torch.inference_mode():
        torch.testing.assert_close(model(original)[:, :3], model(changed)[:, :3])


def test_checkpoint_and_math_sdpa_match_cpu_gradients():
    torch.manual_seed(2026)
    base = TinyDecoder()
    tokens = torch.tensor([[1, 2, 3, 4]])
    labels = torch.tensor([[2, 3, 4, 5]])
    base_loss, base_gradient = run_step(base, tokens, labels, "cpu", None)
    # 前一个模型已更新，其他分支要从它更新前的状态开始。
    torch.manual_seed(2026)
    initial = TinyDecoder().state_dict()
    for attention, recompute in (("eager", True), ("sdpa", False)):
        model = TinyDecoder(attention, recompute)
        model.load_state_dict(initial)
        loss, gradient = run_step(
            model,
            tokens,
            labels,
            "cpu",
            SDPBackend.MATH if attention == "sdpa" else None,
        )
        assert loss == pytest.approx(base_loss, abs=1e-6)
        torch.testing.assert_close(gradient, base_gradient, atol=1e-6, rtol=1e-5)


def test_packing_matches_separate_valid_logits_and_gradients():
    torch.manual_seed(2026)
    base = TinyDecoder()
    state = copy.deepcopy(base.state_dict())
    sequences = [[1, 2, 3], [4, 5]]
    padded, packed = padded_batch(sequences), pack_sequences(sequences)
    padded_loss, padded_gradient = run_step(
        base,
        padded["tokens"],
        padded["labels"],
        "cpu",
        None,
        padded["positions"],
        padded["allowed"],
    )
    model = TinyDecoder()
    model.load_state_dict(state)
    packed_loss, packed_gradient = run_step(
        model,
        packed["tokens"],
        packed["labels"],
        "cpu",
        None,
        packed["positions"],
        packed["allowed"],
    )
    assert padded_loss == pytest.approx(packed_loss, abs=1e-6)
    torch.testing.assert_close(padded_gradient, packed_gradient, atol=1e-6, rtol=1e-5)
    assert torch.isfinite(torch.tensor(padded_loss))


def test_no_cross_sample_information_with_packing_mask():
    model = TinyDecoder().eval()
    packed = pack_sequences([[1, 2, 3], [4, 5]])
    changed = packed["tokens"].clone()
    changed[0, :3] = torch.tensor([6, 7, 8])
    with torch.inference_mode():
        first = model(packed["tokens"], packed["positions"], packed["allowed"])
        second = model(changed, packed["positions"], packed["allowed"])
    torch.testing.assert_close(first[:, 3:], second[:, 3:])


def test_checkpoint_recomputes_blocks_during_backward():
    model = TinyDecoder(checkpoint_layers=True)
    calls = []
    original = model.blocks[0].forward

    def counted(*args):
        calls.append(1)
        return original(*args)

    model.blocks[0].forward = counted
    logits = model(torch.tensor([[1, 2, 3]]))
    F.cross_entropy(logits.reshape(-1, 64), torch.tensor([2, 3, 4])).backward()
    assert len(calls) == 2


def test_unavailable_flash_is_explicit_not_silent_math_fallback(tmp_path):
    if not torch.backends.cuda.is_flash_attention_available():
        with pytest.raises(ValueError, match="没有可用Flash"):
            run(tmp_path / "not-created", "cpu", (8,), "flash")
        assert not (tmp_path / "not-created").exists()


@pytest.mark.skipif(
    not torch.cuda.is_available() or not torch.cuda.is_bf16_supported(),
    reason="缺少BF16 CUDA",
)
def test_actual_cuda_backward_and_checkpoint_agreement():
    torch.manual_seed(2026)
    model = TinyDecoder().cuda()
    state = copy.deepcopy(model.state_dict())
    tokens = torch.tensor([[1, 2, 3, 4]], device="cuda")
    labels = torch.tensor([[2, 3, 4, 5]], device="cuda")
    loss, gradient = run_step(model, tokens, labels, "cuda", None)
    recomputed = TinyDecoder(checkpoint_layers=True).cuda()
    recomputed.load_state_dict(state)
    other_loss, other_gradient = run_step(recomputed, tokens, labels, "cuda", None)
    torch.cuda.synchronize()
    assert loss == other_loss and torch.equal(gradient, other_gradient)


@pytest.mark.skipif(not torch.distributed.is_gloo_available(), reason="Gloo不可用")
def test_real_two_process_ddp_matches_reference_update(tmp_path):
    output = tmp_path / "ddp"
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parent / "distributed_demo.py"),
            "--output-dir",
            str(output),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    assert report["world_size"] == 2 and report["max_abs_difference"] == 0
    assert report["reference_weights"][0] == pytest.approx([0.9875, 0.1625])
