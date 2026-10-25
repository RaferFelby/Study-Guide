"""工具轨迹、监督边界、实际执行与微型训练的行为检查。"""

import copy

import pytest
import torch

import evaluation
from data import (
    TOKENS,
    batch_rows,
    chat_rows,
    encode,
    make_tasks,
    make_trace,
    make_training_rows,
    prepare_traces,
    validate_trace,
)
from experiment import save_weights
from model import TinyToolModel, generate
from tools import (
    ToolUnavailable,
    execute_tool,
    make_catalog,
    parse_call,
    semantic_checks,
)
from training import train_model


def test_trace_filter_preserves_raw_failures():
    raw, valid, rejected = prepare_traces()
    assert (len(raw), len(valid), len(rejected)) == (52, 48, 4)
    assert [row["raw_index"] for row in rejected] == [48, 49, 50, 51]
    assert raw[48]["action"][3] == "get_size"


def test_case_groups_disjoint_but_entities_overlap():
    train, dev, test = (make_tasks(name) for name in ("train", "dev", "test"))
    assert {row["source_id"] for row in train}.isdisjoint(
        {row["source_id"] for row in dev + test}
    )
    assert {row["entity_id"] for row in train} == {row["entity_id"] for row in test}


@pytest.mark.parametrize(
    "tokens",
    [
        [],
        ["plan"] * 6,
        ["plan", "color", "call", "shell", "item-0", "<eos>"],
        ["plan", "color", "call", "get_color", "item-99", "<eos>"],
    ],
)
def test_invalid_call_rejected(tokens):
    with pytest.raises(ValueError):
        parse_call(tokens)


def test_grammar_does_not_prove_semantics():
    task = make_tasks()[0]
    call = parse_call(["plan", "color", "call", "get_size", "item-0", "<eos>"])
    assert semantic_checks(call, task) == {
        "plan_correct": True,
        "tool_correct": False,
        "argument_correct": True,
    }


def test_executor_uses_current_catalog():
    assert execute_tool("get_color", "item-0", make_catalog()) == "red"
    assert execute_tool("get_color", "item-0", make_catalog(True)) == "blue"
    with pytest.raises(ToolUnavailable):
        execute_tool("get_color", "item-0", make_catalog(), unavailable=True)
    with pytest.raises(ValueError):
        execute_tool("shell", "item-0", make_catalog())


def test_provenance_and_observation_checked():
    trace = make_trace(make_tasks()[0])
    trace["origin"] = "unknown"
    with pytest.raises(ValueError, match="来源"):
        validate_trace(trace)
    trace = make_trace(make_tasks()[0])
    trace["observation"] = "blue"
    with pytest.raises(ValueError, match="观察"):
        validate_trace(trace)


def test_rows_use_correct_refusal_and_explicit_replay():
    plain, replay = make_training_rows(), make_training_rows(True)
    assert (len(plain), len(replay)) == (108, 116)
    assert all(answer == ["refuse", "unavailable", "<eos>"] for _, answer in plain[96:])
    assert replay[-8:] == chat_rows() * 4


def test_context_and_observation_are_not_targets():
    rows = make_training_rows()[:2]
    inputs, labels = batch_rows(rows)
    assert inputs.shape == labels.shape == (2, 15)
    assert (labels[0, :4] == -100).all()
    assert (labels[1, :12] == -100).all()
    assert (labels[0] != -100).sum().item() == 6
    assert (labels[1] != -100).sum().item() == 3
    assert (labels[0, 10:] == -100).all()


@pytest.mark.parametrize(
    "rows",
    [[], [([], ["<eos>"])], [(["query"], ["red"])], [(["query"] * 24, ["<eos>"])]],
)
def test_invalid_training_rows_fail(rows):
    with pytest.raises(ValueError):
        batch_rows(rows)


def test_unknown_token_fails():
    with pytest.raises(ValueError):
        encode(["unregistered"])


def install_responses(monkeypatch, responses, contexts=None):
    iterator = iter(responses)

    def fake_generate(model, prompt):
        if contexts is not None:
            contexts.append(prompt)
        return next(iterator)

    monkeypatch.setattr(evaluation, "generate", fake_generate)


def test_semantic_rejection_never_executes_or_repairs(monkeypatch):
    task = make_tasks()[0]
    install_responses(
        monkeypatch, [["plan", "color", "call", "get_size", "item-0", "<eos>"]]
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("错误工具不得执行")

    monkeypatch.setattr(evaluation, "execute_tool", forbidden)
    result = evaluation.run_episode(None, task)
    assert result["format_valid"] and not result["semantic_valid"]
    assert result["tool_calls"] == 0 and result["status"] == "semantic_rejected"
    assert result["action"][3] == "get_size"


def test_actual_observation_reaches_second_generation(monkeypatch):
    task = make_tasks()[0]
    contexts = []
    install_responses(
        monkeypatch, [make_trace(task)["action"], ["final", "blue", "<eos>"]], contexts
    )
    result = evaluation.run_episode(None, task, make_catalog(True))
    assert result["end_to_end"] and result["observation"] == "blue"
    assert contexts[1][-2:] == ["observation", "blue"]


def test_executed_tool_with_wrong_final_is_not_success(monkeypatch):
    task = make_tasks()[0]
    install_responses(
        monkeypatch, [make_trace(task)["action"], ["final", "blue", "<eos>"]]
    )
    result = evaluation.run_episode(None, task)
    assert result["execution_success"] and not result["end_to_end"]


def test_unavailable_cannot_become_completed_from_hallucinated_final(monkeypatch):
    task = make_tasks()[0]
    contexts = []
    install_responses(
        monkeypatch, [make_trace(task)["action"], ["final", "red", "<eos>"]], contexts
    )
    result = evaluation.run_episode(None, task, unavailable=True)
    assert result["tool_calls"] == 1 and result["status"] == "unavailable"
    assert not result["execution_success"] and not result["end_to_end"]
    assert contexts[1][-2:] == ["error", "unavailable"]


def test_summary_uses_same_task_denominator(monkeypatch):
    task = make_tasks()[0]
    install_responses(
        monkeypatch, [make_trace(task)["action"], ["final", "red", "<eos>"], []]
    )
    good = evaluation.run_episode(None, task)
    bad = evaluation.run_episode(None, task)
    summary = evaluation.summarize([good, bad])
    assert summary["n"] == 2
    assert summary["format_valid"] == summary["end_to_end"] == 1


def test_gru_has_no_future_information():
    torch.manual_seed(1)
    model = TinyToolModel().eval()
    left = torch.tensor([encode(["query", "color", "item-0", "case-00"])])
    right = left.clone()
    right[0, -1] = 5
    with torch.inference_mode():
        assert torch.equal(model(left)[:, :3], model(right)[:, :3])


@pytest.mark.parametrize("limit", [0, 9, True])
def test_generation_limit_rejected(limit):
    with pytest.raises(ValueError):
        generate(TinyToolModel(), ["chat", "red"], limit)


def test_generation_stops_at_eos_or_explicit_cap():
    model = TinyToolModel()
    with torch.no_grad():
        model.output.weight.zero_()
        model.output.bias.zero_()
        model.output.bias[1] = 10
    assert generate(model, ["chat", "red"]) == ["<eos>"]
    with torch.no_grad():
        model.output.bias[1] = 0
        model.output.bias[TOKENS.index("red")] = 10
    assert generate(model, ["chat", "red"], 8) == ["red"] * 8


def test_actual_cpu_training_changes_weights_and_reduces_loss():
    torch.set_num_threads(2)
    torch.manual_seed(2026)
    model = TinyToolModel()
    before = copy.deepcopy(model.state_dict())
    history = train_model(model, chat_rows(), 20)
    assert history[-1]["loss_before_update"] < history[0]["loss_before_update"]
    assert any(
        not torch.equal(before[name], value)
        for name, value in model.state_dict().items()
    )


@pytest.mark.skipif(not torch.cuda.is_available(), reason="本机没有CUDA")
def test_actual_cuda_update():
    model = TinyToolModel().cuda()
    before = model.output.weight.detach().clone()
    train_model(model, chat_rows(), 2)
    torch.cuda.synchronize()
    assert not torch.equal(before, model.output.weight)


def test_saved_weights_are_for_inference_and_not_resume(tmp_path):
    path = tmp_path / "weights.pt"
    original = TinyToolModel()
    save_weights(path, original)
    saved = torch.load(path, weights_only=True)
    assert saved["purpose"] == "inference_only_not_exact_resume"
    assert saved["vocabulary"] == TOKENS and "optimizer" not in saved
    restored = TinyToolModel()
    restored.load_state_dict(saved["weights"])
    assert generate(restored, ["chat", "red"]) == generate(original, ["chat", "red"])


def test_untrained_tool_and_entity_absent_from_training():
    rows = make_training_rows()
    tokens = {token for prompt, answer in rows for token in prompt + answer}
    assert "shape" not in tokens and "item-6" not in tokens
    assert execute_tool("get_shape", "item-6", make_catalog()) == "round"
