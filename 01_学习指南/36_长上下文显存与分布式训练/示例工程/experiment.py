"""固定数据与初始化测训练一步；显式记录SDPA后端。"""

import argparse
import copy
import json
import platform
import statistics
import time
from contextlib import nullcontext
from pathlib import Path

import torch
from torch.nn import functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from model import HEADS, LAYERS, TinyDecoder
from planning import attention_matrix_bytes


def run_step(model, tokens, labels, device, backend, positions=None, allowed=None):
    precision = (
        torch.autocast("cuda", dtype=torch.bfloat16)
        if device == "cuda"
        else nullcontext()
    )
    kernel = sdpa_kernel(backend) if backend is not None else nullcontext()
    optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
    model.train()
    optimizer.zero_grad(set_to_none=True)
    with precision, kernel:
        logits = model(tokens, positions, allowed)
        loss = F.cross_entropy(
            logits.float().reshape(-1, logits.shape[-1]),
            labels.reshape(-1),
            ignore_index=-100,
        )
    if not torch.isfinite(loss):
        raise FloatingPointError("损失非有限")
    loss.backward()
    gradients = torch.cat(
        [parameter.grad.flatten() for parameter in model.parameters()]
    )
    if not torch.isfinite(gradients).all():
        raise FloatingPointError("梯度非有限")
    optimizer.step()
    return float(loss.detach()), gradients.detach().cpu()


def benchmark_case(length, device, sdpa_backend="math"):
    torch.manual_seed(2026)
    generator = torch.Generator().manual_seed(2000 + length)
    tokens = torch.randint(1, 64, (2, length), generator=generator).to(device)
    labels = (tokens % 63) + 1
    base = TinyDecoder().to(device)
    weights = copy.deepcopy(base.state_dict())
    del base
    cases, baseline_loss, baseline_gradient = [], None, None
    for name, attention, recompute in (
        ("eager", "eager", False),
        ("checkpoint", "eager", True),
        ("sdpa", "sdpa", False),
    ):
        backend = (
            None
            if attention == "eager"
            else SDPBackend.FLASH_ATTENTION
            if sdpa_backend == "flash"
            else SDPBackend.MATH
        )
        model = TinyDecoder(attention, recompute).to(device)
        model.load_state_dict(weights)
        run_step(
            model, tokens, labels, device, backend
        )  # 预热不进入计时，测量前恢复同一权重。
        times, peaks, reserved, measured_loss, measured_gradient = (
            [],
            [],
            [],
            None,
            None,
        )
        for _ in range(3):
            model.load_state_dict(weights)
            model.zero_grad(set_to_none=True)
            if device == "cuda":
                torch.cuda.synchronize()
                torch.cuda.reset_peak_memory_stats()
            started = time.perf_counter()
            measured_loss, measured_gradient = run_step(
                model, tokens, labels, device, backend
            )
            if device == "cuda":
                torch.cuda.synchronize()
                peaks.append(torch.cuda.max_memory_allocated())
                reserved.append(torch.cuda.max_memory_reserved())
            times.append(time.perf_counter() - started)
        if baseline_loss is None:
            baseline_loss, baseline_gradient = measured_loss, measured_gradient
        cases.append(
            {
                "length": length,
                "variant": name,
                "attention_backend": "explicit_eager"
                if backend is None
                else str(backend),
                "median_seconds": statistics.median(times),
                "times_seconds": times,
                "tokens_per_second": tokens.numel() / statistics.median(times),
                "peak_allocated_bytes": max(peaks) if peaks else None,
                "peak_reserved_bytes": max(reserved) if reserved else None,
                "loss_before_update": measured_loss,
                "loss_abs_difference": abs(measured_loss - baseline_loss),
                "gradient_max_abs_difference": float(
                    (measured_gradient - baseline_gradient).abs().max()
                ),
                "dense_score_matrix_bytes_one_layer_fp32": attention_matrix_bytes(
                    2, HEADS, length
                ),
                "layers": LAYERS,
            }
        )
        del model
    return cases


def run(output_dir, device="cpu", lengths=(64, 128, 256, 512), sdpa_backend="math"):
    if device not in {"cpu", "cuda"} or (
        device == "cuda"
        and (not torch.cuda.is_available() or not torch.cuda.is_bf16_supported())
    ):
        raise ValueError("需可用CPU，或支持BF16的CUDA设备")
    if not lengths or any(
        type(length) is not int or not 8 <= length <= 1024 for length in lengths
    ):
        raise ValueError("长度需为8～1024的整数")
    if sdpa_backend not in {"math", "flash"}:
        raise ValueError("SDPA后端需为math或flash")
    if sdpa_backend == "flash" and (
        device != "cuda" or not torch.backends.cuda.is_flash_attention_available()
    ):
        raise ValueError(
            "当前设备或构建没有可用FlashAttention；math结果不能写成Flash结果"
        )
    torch.set_num_threads(2)
    results = []
    for length in lengths:
        results.extend(benchmark_case(length, device, sdpa_backend))
    report = {
        "scope": "small_decoder_one_training_step_no_long_context_quality_claim",
        "python": platform.python_version(),
        "torch": torch.__version__,
        "device": device,
        "gpu": torch.cuda.get_device_name(0) if device == "cuda" else None,
        "precision": "autocast_bf16_fp32_weights_and_loss"
        if device == "cuda"
        else "fp32",
        "optimizer": "SGD_without_momentum",
        "batch_size": 2,
        "seed": 2026,
        "flash_attention_built": torch.backends.cuda.is_flash_attention_available(),
        "parameters": sum(
            parameter.numel() for parameter in TinyDecoder().parameters()
        ),
        "memory_scope": "CUDA_allocator_peak_including_live_weights_snapshots_inputs_gradients_and_temporaries_not_device_total",
        "timing_scope": "forward_loss_backward_gradient_check_SGD_update_and_gradient_CPU_copy_not_data_loading",
        "warmup": 1,
        "repeats": 3,
        "results": results,
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--sdpa-backend", choices=["math", "flash"], default="math")
    parser.add_argument("--lengths", type=int, nargs="+", default=[64, 128, 256, 512])
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.output_dir, args.device, tuple(args.lengths), args.sdpa_backend)
    print(report["device"], report["parameters"], report["precision"])
    for row in report["results"]:
        print(
            row["length"],
            row["variant"],
            round(row["median_seconds"], 5),
            row["peak_allocated_bytes"],
            round(row["loss_abs_difference"], 6),
        )


if __name__ == "__main__":
    main()
