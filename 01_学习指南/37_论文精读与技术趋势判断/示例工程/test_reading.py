"""卡片结构、决策失败优先与实际低秩合并机制。"""

import copy

import pytest
import torch
from torch.nn import functional as F

from catalog import reading_cards
from decision import decide, lora_demo_facts
from evidence import compare_conditions, validate_claim, validate_note
from merge_probe import AdaptedLinear, compare_merge, run
from review import run as run_review


def test_all_six_notes_answer_four_questions():
    cards = reading_cards()
    assert len(cards) == 6 and len({card["id"] for card in cards}) == 6
    for card in cards:
        assert validate_note(card) is card
    cards[0]["problem"] = "changed"
    assert reading_cards()[0]["problem"] != "changed"


@pytest.mark.parametrize(
    "field",
    ["problem", "method", "evidence", "limitations", "locator", "reading_depth"],
)
def test_missing_note_detail_fails(field):
    note = reading_cards()[0]
    note[field] = ""
    with pytest.raises(ValueError):
        validate_note(note)


def test_note_type_and_source_checked():
    with pytest.raises(TypeError):
        validate_note([])
    note = reading_cards()[0]
    note["source"] = "just a title"
    with pytest.raises(ValueError):
        validate_note(note)


def test_claim_scope_and_unknown_not_verified():
    claim = {
        "kind": "local_mechanism",
        "statement": "线性合并近似等价",
        "scope": "固定FP32小矩阵",
        "locator": "local/report.json",
        "verified": True,
    }
    assert validate_claim(claim) is claim
    with pytest.raises(ValueError):
        validate_claim(dict(claim, kind="unknown"))
    with pytest.raises(ValueError):
        validate_claim(dict(claim, scope=""))


def test_condition_difference_and_unknown_visible():
    rows = compare_conditions(
        {"model": "same", "updates": 100}, {"model": "same", "updates": 200}
    )
    assert {row["field"]: row["status"] for row in rows}["updates"] == "different"
    assert {row["field"]: row["status"] for row in rows}["dataset"] == "unknown"


def test_decision_stances_and_failure_priority():
    facts = lora_demo_facts()
    assert decide(facts)["stance"] == "试点"
    assert decide(dict(facts, business_pilot_passed=True))["stance"] == "采用"
    assert decide(dict(facts, backend_ready=False))["stance"] == "观望"
    assert decide(dict(facts, rollback_ready=False))["stance"] == "观望"
    assert decide(dict(facts, needed=False))["stance"] == "不采用"
    assert (
        decide(dict(facts, business_pilot_passed=True, critical_failure=True))["stance"]
        == "不采用"
    )
    assert decide(dict(facts, mechanism_passed=False))["stance"] == "观望"


@pytest.mark.parametrize(
    "mutation", [{"needed": "yes"}, {"extra": True}, {"needed": None}]
)
def test_decision_does_not_guess_missing_facts(mutation):
    facts = dict(lora_demo_facts(), **mutation)
    with pytest.raises(ValueError):
        decide(facts)


def test_merge_nonzero_update_and_missing_scale_negative_control():
    torch.manual_seed(2026)
    model = AdaptedLinear()
    before = copy.deepcopy(model.state_dict())
    result = compare_merge(model, torch.randn(4, 8))
    assert result["passed"] and result["missing_scale_max_abs_difference"] > 1e-4
    assert all(
        torch.equal(before[name], value) for name, value in model.state_dict().items()
    )


def test_zero_b_initialization_is_identity_and_first_a_gradient_zero():
    model = AdaptedLinear(zero_b=True)
    inputs = torch.randn(4, 8)
    torch.testing.assert_close(
        model(inputs), F.linear(inputs, model.base_weight, model.bias)
    )
    F.mse_loss(model(inputs), torch.ones(4, 6)).backward()
    assert torch.equal(model.matrix_a.grad, torch.zeros_like(model.matrix_a))
    assert model.matrix_b.grad.abs().sum() > 0
    assert model.base_weight.grad is None


@pytest.mark.parametrize("rank", [0, 9, True])
def test_invalid_rank_rejected(rank):
    with pytest.raises(ValueError):
        AdaptedLinear(rank=rank)


@pytest.mark.parametrize("alpha", [float("nan"), float("inf")])
def test_nonfinite_scale_rejected(alpha):
    with pytest.raises(ValueError):
        AdaptedLinear(alpha=alpha)


def test_large_rank_does_not_guarantee_parameter_saving():
    model = AdaptedLinear(rank=4)
    assert model.matrix_a.numel() + model.matrix_b.numel() == 56
    assert model.base_weight.numel() == 48


def test_actual_cpu_probe_and_no_overwrite(tmp_path):
    output = tmp_path / "cpu"
    report = run(output, "cpu")
    assert (
        report["base_frozen"]
        and report["before"]["passed"]
        and report["after"]["passed"]
    )
    assert report["adapter_parameters"] == 28 and report["base_weight_parameters"] == 48
    assert not report["task_quality_measured"] and not report["speed_measured"]
    with pytest.raises(FileExistsError):
        run(output, "cpu")


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA不可用")
def test_actual_cuda_probe(tmp_path):
    report = run(tmp_path / "cuda", "cuda")
    assert report["base_frozen"] and report["after"]["passed"]


def test_structured_review_is_not_business_validation(tmp_path):
    report = run_review(tmp_path / "review")
    assert report["decision"]["stance"] == "试点"
    assert not report["decision_facts"]["business_pilot_passed"]
    assert "not_automatic_fact_check" in report["scope"]
