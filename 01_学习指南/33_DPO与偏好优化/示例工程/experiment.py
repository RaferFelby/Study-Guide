"""实际微型模型Base→SFT checkpoint→两类DPO；不用外部权重。"""

import argparse
import copy
import json
import platform
import time
from pathlib import Path

import torch

from data import TOKENS, make_pairs
from evaluation import evaluate
from model import TinyLanguageModel
from training import make_reference, train_dpo, train_sft


def save_weights(path, model):
    torch.save(
        {
            "vocabulary": TOKENS,
            "weights": {
                name: value.detach().cpu() for name, value in model.state_dict().items()
            },
            "purpose": "inference_weights_not_resume_checkpoint",
        },
        path,
    )


def load_weights(path, device="cpu"):
    state = torch.load(path, map_location="cpu", weights_only=True)
    if state["vocabulary"] != TOKENS:
        raise ValueError("推理权重词表不匹配")
    model = TinyLanguageModel().to(device)
    model.load_state_dict(state["weights"])
    return model


def run_experiment(output_dir, device="cpu"):
    if device not in {"cpu", "cuda"} or (
        device == "cuda" and not torch.cuda.is_available()
    ):
        raise ValueError("设备需为可用cpu/cuda")
    output_dir.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(2)
    torch.manual_seed(2026)
    if device == "cuda":
        torch.cuda.manual_seed_all(2026)
        torch.cuda.reset_peak_memory_stats()
    train_pairs = make_pairs("train")
    test_pairs = make_pairs("test")
    model = TinyLanguageModel().to(device)
    # 本地Base先学旧copy任务；只用训练来源，不是通用预训练模型。
    train_sft(
        model,
        [["copy", *pair["prompt"][1:]] for pair in train_pairs],
        [[pair["color"], "<eos>"] for pair in train_pairs],
        100,
    )
    save_weights(output_dir / "base.pt", model)
    base = evaluate(model, test_pairs)
    prompts = [pair["prompt"] for pair in train_pairs]
    completions = [
        pair["chosen"] if index % 4 == 0 else pair["rejected"]
        for index, pair in enumerate(train_pairs)
    ]
    train_sft(model, prompts, completions, 150)
    save_weights(output_dir / "sft.pt", model)
    # 显式从保存的SFT权重加载，再复制独立参考。
    sft_model = load_weights(output_dir / "sft.pt", device)
    sft = evaluate(sft_model, test_pairs)
    reference = make_reference(sft_model)
    reference_before = {
        name: value.clone() for name, value in reference.state_dict().items()
    }
    runs = []
    for label, biased, beta, updates, learning_rate in (
        ("clean-beta-0.1", False, 0.1, 80, 0.001),
        ("clean-beta-0.5", False, 0.5, 80, 0.001),
        ("biased-short", True, 0.1, 200, 0.001),
        ("aggressive-clean", False, 0.1, 80, 0.01),
    ):
        policy = copy.deepcopy(sft_model)
        started = time.perf_counter()
        history = train_dpo(
            policy, reference, make_pairs("train", biased), beta, updates, learning_rate
        )
        if device == "cuda":
            torch.cuda.synchronize()
        elapsed = time.perf_counter() - started
        save_weights(output_dir / f"{label}.pt", policy)
        runs.append(
            {
                "name": label,
                "beta": beta,
                "updates": updates,
                "learning_rate": learning_rate,
                "biased": biased,
                "history": history,
                "training_seconds": elapsed,
                "dev": evaluate(policy, make_pairs("dev")),
                "test": evaluate(policy, test_pairs),
                "biased_pair_test": evaluate(policy, make_pairs("test", True))
                if biased
                else None,
            }
        )
    assert all(
        torch.equal(reference_before[name], value)
        for name, value in reference.state_dict().items()
    )
    assert all(parameter.grad is None for parameter in reference.parameters())
    report = {
        "scope": "actual_tiny_gru_dpo_with_synthetic_preferences",
        "evaluation_protocol": "fixed_diagnostic_not_blind_final_test",
        "python": platform.python_version(),
        "torch": torch.__version__,
        "device": device,
        "precision": "fp32",
        "gpu": torch.cuda.get_device_name(0) if device == "cuda" else None,
        "seed": 2026,
        "parameters": sum(parameter.numel() for parameter in model.parameters()),
        "pairs": {"train": 48, "dev": 12, "test": 12},
        "base": base,
        "sft": sft,
        "runs": runs,
        "reference_unchanged": True,
        "cuda_peak_allocated_bytes": torch.cuda.max_memory_allocated()
        if device == "cuda"
        else None,
        "real_human_preferences": False,
        "ppo_executed": False,
        "resume_training_supported": False,
    }
    with (output_dir / "report.json").open("x", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    args = parser.parse_args()
    report = run_experiment(args.output_dir, args.device)
    print(
        json.dumps(
            {
                "device": report["device"],
                "base": {
                    key: value
                    for key, value in report["base"].items()
                    if key != "details"
                },
                "sft": {
                    key: value
                    for key, value in report["sft"].items()
                    if key != "details"
                },
                "dpo": [
                    {
                        "name": run["name"],
                        "test": {
                            key: value
                            for key, value in run["test"].items()
                            if key != "details"
                        },
                        "seconds": run["training_seconds"],
                    }
                    for run in report["runs"]
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
