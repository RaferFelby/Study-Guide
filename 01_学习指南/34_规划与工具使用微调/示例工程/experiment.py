"""实际小模型工具SFT，比较仅工具与混合旧任务重放。"""

import argparse
import copy
import json
import platform
import time
from pathlib import Path

import torch

from data import TOKENS, chat_rows, make_training_rows, prepare_traces
from evaluation import evaluate_model
from model import TinyToolModel
from training import train_model


def save_weights(path, model):
    torch.save(
        {
            "vocabulary": TOKENS,
            "weights": {
                name: value.detach().cpu() for name, value in model.state_dict().items()
            },
            "purpose": "inference_only_not_exact_resume",
        },
        path,
    )


def run_experiment(output_dir, device="cpu"):
    if device not in {"cpu", "cuda"} or (
        device == "cuda" and not torch.cuda.is_available()
    ):
        raise ValueError("需要可用cpu/cuda")
    output_dir.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(2)
    torch.manual_seed(2026)
    if device == "cuda":
        torch.cuda.manual_seed_all(2026)
        torch.cuda.reset_peak_memory_stats()
    base = TinyToolModel().to(device)
    train_model(base, chat_rows(), 100)
    save_weights(output_dir / "base.pt", base)
    evaluations = {"base": evaluate_model(base)}
    training_records = {}
    for label, replay in (("tool_only", False), ("with_replay", True)):
        policy = copy.deepcopy(base)
        rows = make_training_rows(replay)
        started = time.perf_counter()
        history = train_model(policy, rows, 200)
        if device == "cuda":
            torch.cuda.synchronize()
        elapsed = time.perf_counter() - started
        save_weights(output_dir / f"{label}.pt", policy)
        evaluations[label] = evaluate_model(policy)
        training_records[label] = {
            "rows": len(rows),
            "updates": 200,
            "learning_rate": 0.01,
            "history": history,
            "training_seconds": elapsed,
        }
    raw, valid, rejected = prepare_traces()
    with (output_dir / "raw_traces.jsonl").open("x", encoding="utf-8") as file:
        for trace in raw:
            file.write(json.dumps(trace, ensure_ascii=False) + "\n")
    report = {
        "scope": "actual_tiny_gru_tool_finetuning_with_synthetic_readonly_executor",
        "python": platform.python_version(),
        "torch": torch.__version__,
        "device": device,
        "precision": "fp32",
        "seed": 2026,
        "parameters": sum(parameter.numel() for parameter in base.parameters()),
        "gpu": torch.cuda.get_device_name(0) if device == "cuda" else None,
        "cuda_peak_allocated_bytes": torch.cuda.max_memory_allocated()
        if device == "cuda"
        else None,
        "trace_counts": {"raw": len(raw), "valid": len(valid), "rejected": rejected},
        "training": training_records,
        "evaluations": evaluations,
        "source_split": "case_ids_disjoint_but_entities_shared",
        "evaluation_protocol": "fixed_diagnostic_not_blind_benchmark",
        "human_data": False,
        "external_tools": False,
        "max_calls_per_episode": 1,
        "max_generated_tokens_per_turn": 8,
        "resume_supported": False,
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
                "parameters": report["parameters"],
                "traces": report["trace_counts"],
                "metrics": {
                    name: {
                        "normal": {
                            key: value
                            for key, value in result["normal"].items()
                            if key != "details"
                        },
                        "changed_success": result["changed_catalog"]["end_to_end"],
                        "unseen_tool": result["unseen_tool"]["end_to_end"],
                        "unseen_entity": result["unseen_entity"]["end_to_end"],
                        "old_chat": result["old_chat"]["correct"],
                    }
                    for name, result in report["evaluations"].items()
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
