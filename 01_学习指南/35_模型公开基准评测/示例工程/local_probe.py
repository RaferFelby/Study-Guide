"""隔离进程加载单元34权重，实际重评微调前后；非公开基准。"""

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path


def run(weights_dir, output_dir, device="cpu"):
    import torch

    # 本进程只选一个单元的data/model；不设置全局PYTHONPATH。
    project = Path(__file__).resolve().parents[2] / "34_规划与工具使用微调/示例工程"
    sys.path.insert(0, str(project))
    from data import TOKENS, make_tasks
    from evaluation import evaluate_model
    from model import TinyToolModel

    if device not in {"cpu", "cuda"} or (
        device == "cuda" and not torch.cuda.is_available()
    ):
        raise ValueError("选择可用cpu或cuda")
    torch.set_num_threads(2)
    paths = {name: weights_dir / f"{name}.pt" for name in ("base", "tool_only")}
    models, hashes = {}, {}
    for name, path in paths.items():
        checkpoint = torch.load(path, map_location=device, weights_only=True)
        if (
            checkpoint["vocabulary"] != TOKENS
            or checkpoint["purpose"] != "inference_only_not_exact_resume"
        ):
            raise ValueError("权重词表或用途不符")
        model = TinyToolModel().to(device)
        model.load_state_dict(checkpoint["weights"])
        models[name] = model
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    runs = []
    for seed in (11, 29, 47):
        torch.manual_seed(seed)
        if device == "cuda":
            torch.cuda.manual_seed_all(seed)
        runs.append(
            {
                "seed": seed,
                "results": {
                    name: evaluate_model(model) for name, model in models.items()
                },
            }
        )
    case_bytes = json.dumps(make_tasks("test"), sort_keys=True).encode()
    report = {
        "scope": "actual_unit34_before_after_generation_synthetic_not_public_benchmark",
        "python": platform.python_version(),
        "torch": torch.__version__,
        "device": device,
        "precision": "fp32",
        "quantization": "none",
        "decoding": "greedy",
        "maximum_new_tokens": 8,
        "weights_sha256": hashes,
        "cases_sha256": hashlib.sha256(case_bytes).hexdigest(),
        "evaluator_sha256": {
            name: hashlib.sha256((project / name).read_bytes()).hexdigest()
            for name in ("data.py", "model.py", "evaluation.py", "tools.py")
        },
        "runs": runs,
        "spread": {
            name: max(row["results"][name]["normal"]["end_to_end"] for row in runs)
            - min(row["results"][name]["normal"]["end_to_end"] for row in runs)
            for name in models
        },
        "note": "greedy_repeats_no_sampling_does_not_measure_training_seed_uncertainty",
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    args = parser.parse_args()
    report = run(args.weights_dir, args.output_dir, args.device)
    print(
        json.dumps(
            {
                "scope": report["scope"],
                "device": report["device"],
                "spread": report["spread"],
                "normal": {
                    name: result["normal"]["end_to_end"]
                    for name, result in report["runs"][0]["results"].items()
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
