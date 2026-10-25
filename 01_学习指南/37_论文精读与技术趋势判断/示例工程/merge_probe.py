"""验证LoRA线性合并和冻结；小随机矩阵，不复现论文任务分数。"""

import argparse
import json
import math
import platform
from pathlib import Path

import torch
from torch import nn
from torch.nn import functional as F


class AdaptedLinear(nn.Module):
    def __init__(
        self, input_features=8, output_features=6, rank=2, alpha=4.0, zero_b=False
    ):
        super().__init__()
        if (
            any(
                type(value) is not int or value < 1
                for value in (input_features, output_features, rank)
            )
            or rank > min(input_features, output_features)
            or not math.isfinite(alpha)
            or alpha <= 0
        ):
            raise ValueError("维度／rank需合法正整数，alpha需正数")
        self.base_weight = nn.Parameter(
            torch.randn(output_features, input_features) * 0.1, requires_grad=False
        )
        self.bias = nn.Parameter(
            torch.randn(output_features) * 0.1, requires_grad=False
        )
        self.matrix_a = nn.Parameter(torch.randn(rank, input_features) * 0.1)
        self.matrix_b = nn.Parameter(
            torch.zeros(output_features, rank)
            if zero_b
            else torch.randn(output_features, rank) * 0.1
        )
        self.scale = alpha / rank

    def forward(self, inputs):
        return F.linear(inputs, self.base_weight, self.bias) + self.scale * F.linear(
            F.linear(inputs, self.matrix_a), self.matrix_b
        )

    def merged_weight(self):
        return self.base_weight.detach().clone() + self.scale * (
            self.matrix_b @ self.matrix_a
        )


@torch.inference_mode()
def compare_merge(model, inputs):
    model.eval()
    branch = model(inputs)
    merged = F.linear(inputs, model.merged_weight(), model.bias)
    wrong_scale = F.linear(
        inputs, model.base_weight + model.matrix_b @ model.matrix_a, model.bias
    )
    return {
        "max_abs_difference": float((branch - merged).abs().max()),
        "missing_scale_max_abs_difference": float((branch - wrong_scale).abs().max()),
        "passed": bool(torch.allclose(branch, merged, atol=1e-6, rtol=1e-5)),
    }


def run(output_dir, device="cpu"):
    if device not in {"cpu", "cuda"} or (
        device == "cuda" and not torch.cuda.is_available()
    ):
        raise ValueError("需要可用CPU或CUDA")
    torch.manual_seed(2026)
    torch.set_num_threads(2)
    torch.set_float32_matmul_precision("highest")
    if device == "cuda":
        torch.backends.cuda.matmul.allow_tf32 = False
    model = AdaptedLinear().to(device)
    inputs = torch.randn(4, 8).to(device)
    targets = torch.randn(4, 6).to(device)
    base_before = model.base_weight.detach().clone()
    before = compare_merge(model, inputs)
    model.train()
    optimizer = torch.optim.SGD([model.matrix_a, model.matrix_b], lr=0.05)
    optimizer.zero_grad(set_to_none=True)
    loss = F.mse_loss(model(inputs), targets)
    if not torch.isfinite(loss):
        raise FloatingPointError("损失非有限")
    loss.backward()
    for parameter in (model.matrix_a, model.matrix_b):
        if not torch.isfinite(parameter.grad).all():
            raise FloatingPointError("梯度非有限")
    optimizer.step()
    after = compare_merge(model, inputs)
    frozen = (
        torch.equal(base_before, model.base_weight) and model.base_weight.grad is None
    )
    if not before["passed"] or not after["passed"] or not frozen:
        raise AssertionError("合并或冻结机制验证失败")
    report = {
        "scope": "LoRA_linear_merge_identity_and_one_step_freezing_not_full_paper_reproduction",
        "paper": "https://arxiv.org/abs/2106.09685v2",
        "locator": "Section 4.1 linear update and merge",
        "python": platform.python_version(),
        "torch": torch.__version__,
        "device": device,
        "gpu": torch.cuda.get_device_name(0) if device == "cuda" else None,
        "precision": "fp32",
        "seed": 2026,
        "input_features": 8,
        "output_features": 6,
        "rank": 2,
        "alpha": 4.0,
        "scale": model.scale,
        "base_weight_parameters": model.base_weight.numel(),
        "adapter_parameters": model.matrix_a.numel() + model.matrix_b.numel(),
        "initialization": "nonzero_B_for_nontrivial_merge_probe_not_original_zero_B_training_init",
        "training_steps": 1,
        "loss_before_update": float(loss.detach()),
        "base_frozen": frozen,
        "before": before,
        "after": after,
        "speed_measured": False,
        "task_quality_measured": False,
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    torch.save(
        {"weights": model.state_dict(), "purpose": "probe_inference_not_exact_resume"},
        output_dir / "probe.pt",
    )
    (output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.output_dir, args.device), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
