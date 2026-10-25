"""固定测试题、贪心生成与偏好打分分别统计，不能互相代替。"""

import torch

from data import batch_sequences
from model import generate
from objectives import sequence_logps


@torch.inference_mode()
def evaluate(model, pairs):
    model.eval()
    device = next(model.parameters()).device
    prompts = [pair["prompt"] for pair in pairs]
    chosen_inputs, chosen_labels = batch_sequences(
        prompts, [pair["chosen"] for pair in pairs], device
    )
    rejected_inputs, rejected_labels = batch_sequences(
        prompts, [pair["rejected"] for pair in pairs], device
    )
    chosen, _ = sequence_logps(model(chosen_inputs), chosen_labels)
    rejected, _ = sequence_logps(model(rejected_inputs), rejected_labels)
    details, factual_correct, exact_brief, copy_correct = [], 0, 0, 0
    for pair in pairs:
        answer = generate(model, pair["prompt"])
        factual = (
            len(answer) >= 3
            and answer[:2] == ["ok", pair["color"]]
            and answer[-1] == "<eos>"
        )
        factual_correct += factual
        exact_brief += answer == ["ok", pair["color"], "<eos>"]
        copy_prompt = ["copy", *pair["prompt"][1:]]
        copy_answer = generate(model, copy_prompt)
        copy_correct += copy_answer == [pair["color"], "<eos>"]
        details.append(
            {
                "source_id": pair["source_id"],
                "color": pair["color"],
                "answer": answer,
                "factual_correct": factual,
                "copy_answer": copy_answer,
            }
        )
    return {
        "n": len(pairs),
        "factual_correct": factual_correct,
        "exact_brief": exact_brief,
        "old_copy_correct": copy_correct,
        "chosen_raw_logp_wins": int((chosen > rejected).sum()),
        "mean_raw_logp_gap": float((chosen - rejected).mean()),
        "details": details,
    }
