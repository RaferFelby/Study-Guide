"""只使用本地合成数据和微型模型；输出目录必须为新的目录。"""

import argparse
import copy
import json
import platform
from pathlib import Path

import torch

from checkpoint import load_adapter, save_adapter, save_training_state, state_digest
from data import (
    TOKENS,
    base_records,
    dataset_digest,
    make_batch,
    make_records,
    split_records,
)
from model import TinyLM, add_lora, merge_lora, parameter_counts
from training import evaluate_generation, evaluate_loss, select_device, train_updates


def make_batches(rows, device, batch_size=16):
    return [
        make_batch(rows[start : start + batch_size], device)
        for start in range(0, len(rows), batch_size)
    ]


def run_experiment(
    output_dir, device_name="cpu", precision="fp32", base_updates=200, sft_updates=250
):
    if (
        type(base_updates) is not int
        or base_updates < 1
        or type(sft_updates) is not int
        or sft_updates < 1
    ):
        raise ValueError("训练更新数需为正整数")
    device = select_device(device_name)
    # 参数校验后才创建目录；实验只在新目录写入，不覆盖旧实验。
    from training import precision_context

    precision_context(device, precision)
    output_dir.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(2)
    torch.manual_seed(2026)
    records = make_records()
    splits = split_records(records)
    batches = make_batches(splits["train"], device)
    base = TinyLM(len(TOKENS)).to(device)
    optimizer = torch.optim.AdamW(base.parameters(), lr=0.02, weight_decay=0.0)
    base_training = train_updates(
        base,
        make_batches(base_records(splits["train"]), device),
        optimizer,
        base_updates,
        device,
        precision=precision,
    )
    base.eval()
    digest = state_digest(base)
    torch.save(
        {"weights": base.state_dict(), "vocabulary": TOKENS, "base_digest": digest},
        output_dir / "base.pt",
    )
    baseline_validation = evaluate_generation(base, splits["validation"], device)
    baseline_loss = evaluate_loss(base, splits["validation"], device)
    baseline_copy = evaluate_generation(
        base, base_records(splits["validation"]), device
    )
    variants = []
    # 两个秩在实验开始前确定；只用验证集选择，测试集最后才读取。
    for rank in (2, 8):
        torch.manual_seed(2027)
        config = {
            "rank": rank,
            "targets": ["q_proj", "v_proj", "lm_head"],
            "dropout": 0.0,
        }
        model = add_lora(
            copy.deepcopy(base), rank, tuple(config["targets"]), config["dropout"]
        )
        optimizer = torch.optim.AdamW(
            [parameter for parameter in model.parameters() if parameter.requires_grad],
            lr=0.02,
            weight_decay=0.0,
        )
        if device.type == "cuda":
            torch.cuda.reset_peak_memory_stats(device)
        training = train_updates(
            model, batches, optimizer, sft_updates, device, precision=precision
        )
        peak_bytes = (
            torch.cuda.max_memory_allocated(device) if device.type == "cuda" else None
        )
        validation = evaluate_generation(model, splits["validation"], device)
        validation_loss = evaluate_loss(model, splits["validation"], device)
        training_loss = evaluate_loss(model, splits["train"], device)
        training_quality = evaluate_generation(model, splits["train"], device)
        copy_retention = evaluate_generation(
            model, base_records(splits["validation"]), device
        )
        adapter_path = output_dir / f"adapter-rank-{rank}.pt"
        save_adapter(adapter_path, model, digest, config)
        training_config = {
            **config,
            "data_digest": dataset_digest(records),
            "device": str(device),
            "precision": precision,
            "batch_size": 16,
            "accumulation": 2,
            "base_lr": 0.02,
            "warmup_attempts": 10,
        }
        save_training_state(
            output_dir / f"training-rank-{rank}.pt",
            model,
            optimizer,
            training["scaler"],
            sft_updates,
            training_config,
        )
        reloaded = load_adapter(adapter_path, base, digest).eval()
        merged = merge_lora(model.eval())
        probe, _ = make_batch(splits["validation"][:4], device)
        with torch.inference_mode():
            logits = model(probe)
            reload_error = (logits - reloaded(probe)).abs().max().item()
            merge_error = (logits - merged(probe)).abs().max().item()
            torch.testing.assert_close(logits, reloaded(probe), atol=1e-5, rtol=1e-5)
            torch.testing.assert_close(logits, merged(probe), atol=2e-5, rtol=1e-5)
        variants.append(
            {
                "rank": rank,
                "parameters": parameter_counts(model),
                "validation": validation,
                "validation_loss": validation_loss,
                "train_loss": training_loss,
                "train_generation": training_quality,
                "copy_retention": copy_retention,
                "training_seconds": training["elapsed_seconds"],
                "cuda_peak_allocated_bytes": peak_bytes,
                "history": training["history"],
                "reload_max_abs_error": reload_error,
                "merge_max_abs_error": merge_error,
                "adapter_bytes": adapter_path.stat().st_size,
            }
        )
        del model, optimizer, reloaded, merged
    selected = min(
        variants,
        key=lambda item: (
            -item["validation"]["passed"],
            item["validation_loss"],
            item["rank"],
        ),
    )
    baseline_test = evaluate_generation(base, splits["test"], device)
    for variant in variants:
        reloaded = load_adapter(
            output_dir / f"adapter-rank-{variant['rank']}.pt", base, digest
        ).eval()
        variant["test"] = evaluate_generation(reloaded, splits["test"], device)
        del reloaded
    improved = selected["test"]["passed"] > baseline_test["passed"]
    report = {
        "scope": "synthetic_tiny_causal_lm_not_pretrained_general_llm",
        "environment": {
            "python": platform.python_version(),
            "torch": str(torch.__version__),
            "device": str(device),
            "precision": precision,
            "gpu": torch.cuda.get_device_name(device)
            if device.type == "cuda"
            else None,
        },
        "recipe": {
            "seed_base": 2026,
            "seed_lora": 2027,
            "base_updates": base_updates,
            "sft_updates": sft_updates,
            "micro_batch_size": 16,
            "accumulation": 2,
            "order": "fixed_cyclic",
            "learning_rate": 0.02,
            "warmup_attempts": 10,
            "weight_decay": 0.0,
            "clip_max_norm": 1.0,
        },
        "data_digest": dataset_digest(records),
        "base_digest": digest,
        "split_counts": {name: len(rows) for name, rows in splits.items()},
        "base": {
            "parameters": parameter_counts(base),
            "training_seconds": base_training["elapsed_seconds"],
            "validation": baseline_validation,
            "validation_loss": baseline_loss,
            "copy_validation": baseline_copy,
            "test": baseline_test,
        },
        "variants": variants,
        "selected_rank": selected["rank"],
        "decision": "improved_on_fixed_toy_test"
        if improved
        else "no_improvement_do_not_adopt",
        "limits": [
            "仅合成固定词表任务",
            "测试组ID未在训练出现，但颜色和输出规则相同",
            "计时为训练循环墙钟，不是通用吞吐基准",
            "CUDA峰值为PyTorch已分配张量内存，包含常驻Base，不代表显卡总占用",
            "CPU峰值内存未测量",
            "测试结果不能证明真实业务收益",
        ],
    }
    (output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def main():
    parser = argparse.ArgumentParser(description="本地微型SFT与LoRA实验，不下载模型")
    parser.add_argument("--device", choices=("cpu", "cuda", "auto"), default="cpu")
    parser.add_argument("--precision", choices=("fp32", "bf16", "fp16"), default="fp32")
    parser.add_argument("--base-updates", type=int, default=200)
    parser.add_argument("--sft-updates", type=int, default=250)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run_experiment(
        args.output_dir,
        args.device,
        args.precision,
        args.base_updates,
        args.sft_updates,
    )
    print(
        json.dumps(
            {
                "environment": report["environment"],
                "counts": report["split_counts"],
                "base_test": report["base"]["test"]["passed"],
                "variants": [
                    {
                        "rank": item["rank"],
                        "test_passed": item["test"]["passed"],
                        "seconds": round(item["training_seconds"], 3),
                        "peak_bytes": item["cuda_peak_allocated_bytes"],
                    }
                    for item in report["variants"]
                ],
                "selected_rank": report["selected_rank"],
                "decision": report["decision"],
                "report": str(args.output_dir / "report.json"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
