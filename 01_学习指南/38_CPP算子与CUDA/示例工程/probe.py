"""先校验再计时；结果只代表当前输入、硬件和同步计时口径。"""

import argparse
import json
import statistics
import time
from pathlib import Path

import torch

from operator_impl import affine


def synchronize(device):
    if device == "cuda":
        torch.cuda.synchronize()


def median_ms(function, value, repeats=15):
    for _ in range(5):
        function(value, 2.0, 1.0)
    synchronize(value.device.type)
    samples = []
    for _ in range(repeats):
        synchronize(value.device.type)
        started = time.perf_counter()
        result = function(value, 2.0, 1.0)
        synchronize(value.device.type)
        samples.append((time.perf_counter() - started) * 1000)
        del result
    return statistics.median(samples)


def native(value, scale, bias):
    return value * scale + bias


def run_probe(device):
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("请求 cuda，但 GPU 不可用；不静默改为 cpu")
    rows = []
    with torch.no_grad():
        for count in (0, 1, 257, 1048576):
            value = torch.linspace(-1, 1, count, device=device)
            expected = native(value, 2.0, 1.0)
            actual = affine(value, 2.0, 1.0)
            synchronize(device)
            torch.testing.assert_close(actual, expected, rtol=1e-5, atol=1e-6)
            error = (actual - expected).abs().max().item() if count else 0.0
            custom_time = median_ms(affine, value)
            native_time = median_ms(native, value)
            rows.append(
                {
                    "count": count,
                    "max_error": error,
                    "custom_ms": custom_time,
                    "native_ms": native_time,
                    "native_over_custom": native_time / custom_time,
                }
            )
    return {
        "torch": torch.__version__,
        "torch_cuda_runtime": torch.version.cuda,
        "cpu_threads": torch.get_num_threads(),
        "device": device,
        "gpu": torch.cuda.get_device_name() if device == "cuda" else None,
        "timing": "15次中位数，5次预热；同步墙钟，含分配/调度，不含编译/数据传输",
        "rows": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--output-dir", type=Path, required=True)
    options = parser.parse_args()
    report = run_probe(options.device)
    options.output_dir.mkdir(parents=True, exist_ok=False)
    (options.output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
