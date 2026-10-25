import copy

import pytest
import torch

from checkpoint import (
    load_adapter,
    load_training_state,
    save_adapter,
    save_training_state,
    state_digest,
)
from data import (
    EOS_ID,
    TOKENS,
    encode,
    make_batch,
    make_records,
    normalize_record,
    split_records,
)
from model import LoRALinear, TinyLM, add_lora, merge_lora, parameter_counts
from training import (
    evaluate_generation,
    precision_context,
    select_device,
    token_loss,
    train_updates,
)


@pytest.fixture(autouse=True)
def bounded_threads():
    torch.set_num_threads(2)


def small_model(dropout=0.0):
    torch.manual_seed(13)
    return add_lora(TinyLM(len(TOKENS)), 2, dropout=dropout)


def test_three_formats_have_same_normalized_tokens():
    instruction = make_records()[0]
    messages = {
        "messages": [
            {"role": "user", "content": "route red item 0 answer :"},
            {"role": "assistant", "content": "tag = R"},
        ],
        "source_group": "item-00",
    }
    conversations = {
        "conversations": [
            {"from": "human", "value": "route red item 0 answer :"},
            {"from": "gpt", "value": "tag = R"},
        ],
        "source_group": "item-00",
    }
    assert (
        normalize_record(instruction)
        == normalize_record(messages)
        == normalize_record(conversations)
    )


@pytest.mark.parametrize(
    "record",
    [
        {},
        {"messages": [1, 2], "source_group": "item-00"},
        {"conversations": [], "source_group": "item-00"},
        {"instruction": 1, "input": "x", "output": "y", "source_group": "item-00"},
    ],
)
def test_bad_format_is_rejected(record):
    with pytest.raises(ValueError):
        normalize_record(record)


def test_source_groups_and_counts_do_not_overlap():
    splits = split_records(make_records())
    assert [len(rows) for rows in splits.values()] == [200, 60, 60]
    groups = [{row["source_group"] for row in rows} for rows in splits.values()]
    assert not (groups[0] & groups[1] or groups[0] & groups[2] or groups[1] & groups[2])


def test_duplicates_and_out_of_range_groups_are_rejected():
    records = make_records()
    with pytest.raises(ValueError, match="重复"):
        split_records(records + [records[0]])
    records[0]["source_group"] = "item--1"
    with pytest.raises(ValueError, match="来源组"):
        split_records(records)


def test_labels_predict_only_answer_including_eos():
    row = normalize_record(make_records()[0])
    shorter = {**row, "answer": ["R", "<eos>"]}
    inputs, labels = make_batch([row, shorter], torch.device("cpu"))
    assert inputs.shape == (2, 9)
    assert labels[0, :5].tolist() == [-100] * 5
    assert labels[0, 5:].tolist() == encode(["tag", "=", "R", "<eos>"])
    assert labels[1, 5:].tolist() == [encode(["R"])[0], EOS_ID, -100, -100]


def test_unknown_token_and_empty_batch_fail():
    with pytest.raises(ValueError, match="词表"):
        encode(["unknown"])
    with pytest.raises(ValueError, match="空"):
        make_batch([], torch.device("cpu"))


def test_causal_attention_cannot_read_future():
    model = TinyLM(len(TOKENS)).eval()
    first = torch.tensor([[2, 5, 7, 14]])
    changed = torch.tensor([[2, 5, 7, 20]])
    with torch.inference_mode():
        assert torch.equal(model(first)[:, :3], model(changed)[:, :3])


def test_lora_zero_initialization_freezing_and_counts():
    base = TinyLM(len(TOKENS)).eval()
    probe = torch.tensor([[2, 5, 7]])
    adapted = add_lora(copy.deepcopy(base), 2).eval()
    with torch.inference_mode():
        assert torch.equal(base(probe), adapted(probe))
    assert parameter_counts(adapted)["trainable"] == 508
    assert all(
        parameter.requires_grad == ("lora_" in name)
        for name, parameter in adapted.named_parameters()
    )


@pytest.mark.parametrize("rank", [0, -1, True, 33])
def test_invalid_rank_is_rejected(rank):
    with pytest.raises(ValueError, match="rank"):
        add_lora(TinyLM(len(TOKENS)), rank)


def test_invalid_and_duplicate_targets_are_rejected():
    with pytest.raises(ValueError):
        add_lora(TinyLM(len(TOKENS)), 2, ("embedding",))
    model = small_model()
    with pytest.raises(ValueError, match="重复"):
        add_lora(model, 2)


def test_merge_requires_eval_and_preserves_logits():
    model = small_model()
    with torch.no_grad():
        model.q_proj.lora_b.normal_(std=0.1)
    with pytest.raises(RuntimeError, match="eval"):
        merge_lora(model)
    model.eval()
    merged = merge_lora(model)
    assert not any(isinstance(layer, LoRALinear) for layer in merged.modules())
    probe = torch.tensor([[2, 5, 7]])
    with torch.inference_mode():
        torch.testing.assert_close(model(probe), merged(probe), atol=1e-5, rtol=1e-5)


def test_adapter_roundtrip_and_base_mismatch(tmp_path):
    base = TinyLM(len(TOKENS))
    digest = state_digest(base)
    model = add_lora(copy.deepcopy(base), 2)
    path = tmp_path / "adapter.pt"
    config = {"rank": 2, "targets": ["q_proj", "v_proj", "lm_head"], "dropout": 0.0}
    save_adapter(path, model, digest, config)
    restored = load_adapter(path, base, digest)
    assert state_digest(model) == state_digest(restored)
    with pytest.raises(ValueError, match="Base"):
        load_adapter(path, base, "wrong")
    with pytest.raises(FileExistsError):
        save_adapter(path, model, digest, config)


def test_token_weighted_accumulation_matches_full_batch():
    rows = split_records(make_records())["train"][:3]
    device = torch.device("cpu")
    first = small_model()
    second = copy.deepcopy(first)
    train_updates(
        first,
        [make_batch(rows[:2], device), make_batch(rows[2:], device)],
        torch.optim.SGD([p for p in first.parameters() if p.requires_grad], lr=0.01),
        1,
        device,
        accumulation=2,
    )
    train_updates(
        second,
        [make_batch(rows, device)],
        torch.optim.SGD([p for p in second.parameters() if p.requires_grad], lr=0.01),
        1,
        device,
        accumulation=1,
    )
    for left, right in zip(first.parameters(), second.parameters(), strict=True):
        torch.testing.assert_close(left, right, atol=1e-7, rtol=1e-6)


def test_exact_cpu_resume_includes_rng_optimizer_and_attempt(tmp_path):
    device = torch.device("cpu")
    batches = [make_batch(split_records(make_records())["train"][:4], device)]
    initial = small_model(dropout=0.2)
    whole = copy.deepcopy(initial)
    partial = copy.deepcopy(initial)
    whole_optimizer = torch.optim.AdamW(
        [p for p in whole.parameters() if p.requires_grad]
    )
    partial_optimizer = torch.optim.AdamW(
        [p for p in partial.parameters() if p.requires_grad]
    )
    torch.manual_seed(99)
    train_updates(whole, batches, whole_optimizer, 4, device)
    torch.manual_seed(99)
    first = train_updates(partial, batches, partial_optimizer, 2, device)
    path = tmp_path / "state.pt"
    config = {"device": "cpu", "data_digest": "fixed", "accumulation": 2}
    save_training_state(path, partial, partial_optimizer, first["scaler"], 2, config)
    restored = copy.deepcopy(initial)
    restored_optimizer = torch.optim.AdamW(
        [p for p in restored.parameters() if p.requires_grad]
    )
    scaler = torch.amp.GradScaler("cuda", enabled=False)
    attempts = load_training_state(path, restored, restored_optimizer, scaler, config)
    train_updates(
        restored,
        batches,
        restored_optimizer,
        2,
        device,
        start_attempt=attempts,
        scaler=scaler,
    )
    assert state_digest(whole) == state_digest(restored)
    with pytest.raises(ValueError, match="配置"):
        load_training_state(
            path, restored, restored_optimizer, scaler, {"device": "cuda"}
        )


def test_empty_supervision_and_cpu_low_precision_are_rejected():
    with pytest.raises(ValueError):
        token_loss(torch.randn(1, 2, len(TOKENS)), torch.full((1, 2), -100))
    with pytest.raises(ValueError):
        precision_context(torch.device("cpu"), "fp16")
    with pytest.raises(ValueError):
        evaluate_generation(TinyLM(len(TOKENS)), [], torch.device("cpu"))
    with pytest.raises(ValueError):
        select_device("metal")


@pytest.mark.parametrize("precision", ["fp32", "bf16", "fp16"])
def test_cuda_precision_updates_are_finite_when_available(precision):
    if not torch.cuda.is_available():
        pytest.skip("无CUDA；GPU路径未执行")
    if precision == "bf16" and not torch.cuda.is_bf16_supported():
        pytest.skip("无bf16硬件支持")
    device = torch.device("cuda")
    model = small_model().to(device)
    batches = [make_batch(split_records(make_records())["train"][:4], device)]
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad])
    result = train_updates(model, batches, optimizer, 3, device, precision=precision)
    assert all(torch.isfinite(torch.tensor(item["loss"])) for item in result["history"])
    assert any(item["applied"] for item in result["history"])
