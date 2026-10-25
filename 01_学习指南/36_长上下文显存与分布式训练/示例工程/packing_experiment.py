"""实际对比padding/packing；密集块掩码可能降低或增加峰值。"""

import argparse
import copy
import json
import statistics
import time
from pathlib import Path

import torch

from experiment import run_step
from model import TinyDecoder
from packing import causal_mask, pack_sequences


def padded_batch(sequences):
    length = max(map(len, sequences))
    tokens = torch.zeros((len(sequences), length), dtype=torch.long)
    labels = torch.full_like(tokens, -100)
    allowed = torch.zeros((len(sequences), 1, length, length), dtype=torch.bool)
    for index, sequence in enumerate(sequences):
        tokens[index, : len(sequence)] = torch.tensor(sequence)
        labels[index, : len(sequence)] = torch.tensor(sequence[1:] + [-100])
        # 填充query不用于loss，但仍有可见key，避免整行softmax(-inf)。
        allowed[index, 0] = causal_mask(length)
        allowed[index, 0, :, len(sequence) :] = False
    return {
        "tokens": tokens,
        "labels": labels,
        "positions": torch.arange(length),
        "allowed": allowed,
    }


def compare_packing(lengths, device="cpu"):
    generator = torch.Generator().manual_seed(2026)
    sequences = [
        torch.randint(1, 64, (length,), generator=generator).tolist()
        for length in lengths
    ]
    batches = {"padding": padded_batch(sequences), "packing": pack_sequences(sequences)}
    torch.manual_seed(2026)
    initial = TinyDecoder().to(device)
    weights = copy.deepcopy(initial.state_dict())
    del initial
    rows, reference_loss, reference_gradient = [], None, None
    for name, batch in batches.items():
        batch = {key: value.to(device) for key, value in batch.items()}
        model = TinyDecoder().to(device)
        model.load_state_dict(weights)
        run_step(
            model,
            batch["tokens"],
            batch["labels"],
            device,
            None,
            batch["positions"],
            batch["allowed"],
        )
        times, peaks = [], []
        for _ in range(3):
            model.load_state_dict(weights)
            model.zero_grad(set_to_none=True)
            if device == "cuda":
                torch.cuda.synchronize()
                torch.cuda.reset_peak_memory_stats()
            started = time.perf_counter()
            loss, gradient = run_step(
                model,
                batch["tokens"],
                batch["labels"],
                device,
                None,
                batch["positions"],
                batch["allowed"],
            )
            if device == "cuda":
                torch.cuda.synchronize()
                peaks.append(torch.cuda.max_memory_allocated())
            times.append(time.perf_counter() - started)
        if reference_loss is None:
            reference_loss, reference_gradient = loss, gradient
        rows.append(
            {
                "variant": name,
                "lengths": lengths,
                "processed_token_slots": batch["tokens"].numel(),
                "supervised_targets": int((batch["labels"] != -100).sum()),
                "median_seconds": statistics.median(times),
                "valid_targets_per_second": int((batch["labels"] != -100).sum())
                / statistics.median(times),
                "peak_allocated_bytes": max(peaks) if peaks else None,
                "loss_before_update": loss,
                "loss_abs_difference": abs(loss - reference_loss),
                "gradient_max_abs_difference": float(
                    (gradient - reference_gradient).abs().max()
                ),
            }
        )
        del model
    return rows


def run(output_dir, device="cpu"):
    if device not in {"cpu", "cuda"} or (
        device == "cuda"
        and (not torch.cuda.is_available() or not torch.cuda.is_bf16_supported())
    ):
        raise ValueError("需可用CPU或BF16 CUDA")
    torch.set_num_threads(2)
    results = {
        "uneven": compare_packing([128, 32, 16, 8], device),
        "equal": compare_packing([64, 64, 64, 64], device),
    }
    report = {
        "scope": "actual_dense_mask_packing_not_flash_varlen",
        "device": device,
        "precision": "autocast_bf16" if device == "cuda" else "fp32",
        "position_reset": True,
        "cross_sample_loss": False,
        "cross_sample_attention": False,
        "results": results,
        "repeats": 3,
        "note": "dense_packed_attention_can_increase_quadratic_work_even_with_fewer_padding_slots",
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.output_dir, args.device), indent=2))


if __name__ == "__main__":
    main()
