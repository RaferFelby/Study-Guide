import copy
import math

import pytest
import torch

from data import TOKENS, batch_sequences, make_pairs, validate_pair
from experiment import load_weights, save_weights
from model import TinyLanguageModel, generate
from objectives import dpo_loss, sequence_logps
from training import make_reference, train_dpo, train_sft


@pytest.fixture(autouse=True)
def small_cpu_threads():
    torch.set_num_threads(2)
    torch.manual_seed(2026)


def test_sources_are_disjoint_and_biased_pair_is_declared():
    sources = [
        {pair["source_id"] for pair in make_pairs(name)}
        for name in ("train", "dev", "test")
    ]
    assert (
        not sources[0] & sources[1]
        and not sources[0] & sources[2]
        and not sources[1] & sources[2]
    )
    assert [len(make_pairs(name)) for name in ("train", "dev", "test")] == [48, 12, 12]
    biased = make_pairs("train", True)[0]
    assert biased["chosen"][1] != biased["color"]
    assert biased["preference_origin"] == "deliberately_wrong_short_fixture"
    validate_pair(biased)


@pytest.mark.parametrize(
    "mutation", ["same", "empty", "eos", "source", "usage", "vocabulary"]
)
def test_invalid_preference_pairs_are_rejected(mutation):
    pair = make_pairs()[0]
    if mutation == "same":
        pair["rejected"] = pair["chosen"]
    elif mutation == "empty":
        pair["chosen"] = []
    elif mutation == "eos":
        pair["chosen"] = ["ok", "red"]
    elif mutation == "source":
        pair["source_id"] = "different"
    elif mutation == "usage":
        pair["usage_policy"] = "unknown"
    else:
        pair["chosen"] = ["not-a-token", "<eos>"]
    with pytest.raises(ValueError):
        validate_pair(pair)


def test_shift_mask_ignores_prompt_and_padding_and_includes_eos():
    logits = torch.zeros(1, 6, 10)
    labels = torch.tensor([[-100, -100, 2, 3, 1, -100]])
    scores, counts = sequence_logps(logits, labels)
    assert counts.tolist() == [3]
    assert scores.item() == pytest.approx(-3 * math.log(10))
    logits[:, 0] = torch.arange(10) * 100
    logits[:, 4] = torch.arange(10) * 100
    assert torch.equal(scores, sequence_logps(logits, labels)[0])


def test_chosen_and_rejected_lengths_are_summed_not_averaged():
    pair = make_pairs()[0]
    inputs, labels = batch_sequences(
        [pair["prompt"]] * 2, [pair["chosen"], pair["rejected"]]
    )
    scores, counts = sequence_logps(torch.zeros(*inputs.shape, len(TOKENS)), labels)
    assert counts.tolist() == [3, 5]
    assert scores[0] > scores[1]
    assert torch.allclose(scores / counts, torch.full((2,), -math.log(len(TOKENS))))


def test_dpo_zero_relative_margin_has_log2_loss_and_gradient_direction():
    chosen = torch.tensor([-2.0], requires_grad=True)
    rejected = torch.tensor([-4.0], requires_grad=True)
    reference_chosen = torch.tensor([-2.0], requires_grad=True)
    reference_rejected = torch.tensor([-4.0], requires_grad=True)
    loss, margin = dpo_loss(chosen, rejected, reference_chosen, reference_rejected, 0.1)
    assert loss.item() == pytest.approx(math.log(2)) and margin.item() == 0
    loss.backward()
    assert chosen.grad.item() < 0 and rejected.grad.item() > 0
    assert reference_chosen.grad is None and reference_rejected.grad is None


@pytest.mark.parametrize("beta", [0, -1, True, float("nan"), float("inf")])
def test_invalid_beta_is_rejected(beta):
    value = torch.tensor([-1.0])
    with pytest.raises(ValueError):
        dpo_loss(value, value, value, value, beta)


def test_extreme_margin_has_finite_loss():
    loss, _ = dpo_loss(
        torch.tensor([-10000.0]),
        torch.tensor([0.0]),
        torch.tensor([0.0]),
        torch.tensor([0.0]),
    )
    assert torch.isfinite(loss) and loss.item() == pytest.approx(1000)


def test_empty_supervision_and_bad_shapes_are_rejected():
    with pytest.raises(ValueError):
        sequence_logps(torch.zeros(1, 3, 10), torch.full((1, 3), -100))
    with pytest.raises(ValueError):
        sequence_logps(torch.zeros(1, 3, 10), torch.zeros(1, 4, dtype=torch.long))


def test_causal_model_cannot_see_future_tokens():
    model = TinyLanguageModel().eval()
    inputs, _ = batch_sequences(
        [make_pairs()[0]["prompt"]], [make_pairs()[0]["chosen"]]
    )
    changed = inputs.clone()
    changed[0, -1] = 3
    with torch.no_grad():
        assert torch.equal(model(inputs)[:, :-1], model(changed)[:, :-1])


def test_dpo_changes_policy_but_not_reference_and_loss_decreases():
    policy = TinyLanguageModel()
    reference = make_reference(policy)
    before_policy = {name: value.clone() for name, value in policy.state_dict().items()}
    before_reference = {
        name: value.clone() for name, value in reference.state_dict().items()
    }
    history = train_dpo(policy, reference, make_pairs()[:4], updates=20)
    assert history[-1]["loss_before_update"] < history[0]["loss_before_update"]
    assert any(
        not torch.equal(before_policy[name], value)
        for name, value in policy.state_dict().items()
    )
    assert all(
        torch.equal(before_reference[name], value)
        for name, value in reference.state_dict().items()
    )
    assert all(
        not parameter.requires_grad and parameter.grad is None
        for parameter in reference.parameters()
    )


def test_unfrozen_or_shared_reference_is_rejected():
    model = TinyLanguageModel()
    with pytest.raises(ValueError):
        train_dpo(model, copy.deepcopy(model), make_pairs()[:2], updates=1)
    model.requires_grad_(False)
    with pytest.raises(ValueError):
        train_dpo(model, model, make_pairs()[:2], updates=1)


def test_sft_weights_reload_and_dpo_starts_from_saved_state(tmp_path):
    model = TinyLanguageModel()
    pairs = make_pairs()[:4]
    train_sft(
        model,
        [pair["prompt"] for pair in pairs],
        [pair["chosen"] for pair in pairs],
        updates=2,
    )
    path = tmp_path / "sft.pt"
    save_weights(path, model)
    restored = load_weights(path)
    assert all(
        torch.equal(value, restored.state_dict()[name])
        for name, value in model.state_dict().items()
    )
    reference = make_reference(restored)
    train_dpo(restored, reference, pairs, updates=1)
    assert len(generate(restored, pairs[0]["prompt"], maximum_tokens=3)) <= 3


@pytest.mark.skipif(not torch.cuda.is_available(), reason="需要已有CUDA设备")
def test_cuda_sft_and_dpo_are_actual_finite_updates():
    model = TinyLanguageModel().cuda()
    pairs = make_pairs()[:4]
    loss = train_sft(
        model,
        [pair["prompt"] for pair in pairs],
        [pair["chosen"] for pair in pairs],
        updates=2,
    )
    history = train_dpo(model, make_reference(model), pairs, updates=2)
    assert math.isfinite(loss) and math.isfinite(history[-1]["loss_before_update"])
