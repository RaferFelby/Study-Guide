"""答案token监督、按token加权梯度累积、AMP/裁剪与有边界训练状态。"""

import math
import time
from contextlib import nullcontext

import torch
from torch.nn import functional as F

from data import EOS_ID, encode, make_batch


def select_device(name):
    if name not in {"cpu", "cuda", "auto"}:
        raise ValueError("device需为cpu/cuda/auto")
    chosen = (
        "cuda"
        if name == "auto" and torch.cuda.is_available()
        else "cpu"
        if name == "auto"
        else name
    )
    if chosen == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("指定CUDA但当前不可用；请检查环境或明确选CPU")
    return torch.device(chosen)


def precision_context(device, precision):
    if precision == "fp32":
        return nullcontext()
    if precision not in {"bf16", "fp16"} or device.type != "cuda":
        raise ValueError("本例低精度仅用于CUDA，CPU明确用fp32")
    if precision == "bf16" and not torch.cuda.is_bf16_supported():
        raise RuntimeError("GPU不支持本例bf16路径")
    return torch.autocast(
        "cuda", dtype=torch.bfloat16 if precision == "bf16" else torch.float16
    )


def token_loss(logits, labels):
    count = (labels != -100).sum().item()
    if count == 0:
        raise ValueError("批次没有答案监督token")
    total = F.cross_entropy(
        logits.float().reshape(-1, logits.shape[-1]),
        labels.reshape(-1),
        ignore_index=-100,
        reduction="sum",
    )
    return total, count


def train_updates(
    model,
    batches,
    optimizer,
    updates,
    device,
    precision="fp32",
    accumulation=2,
    start_attempt=0,
    base_lr=0.02,
    warmup_attempts=10,
    scaler=None,
):
    if (
        type(updates) is not int
        or updates < 1
        or type(accumulation) is not int
        or accumulation < 1
        or not batches
    ):
        raise ValueError("更新数/累积次数需正整数，批次不能空")
    if (
        type(start_attempt) is not int
        or start_attempt < 0
        or not math.isfinite(base_lr)
        or base_lr <= 0
        or type(warmup_attempts) is not int
        or warmup_attempts < 1
    ):
        raise ValueError("起点/学习率/warmup不合法")
    # 创建上下文先校验，避免错误精度在部分更新后才被发现。
    precision_context(device, precision)
    scaler = (
        scaler
        if scaler is not None
        else torch.amp.GradScaler("cuda", enabled=precision == "fp16")
    )
    model.train()
    history = []
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    start = time.perf_counter()
    for attempt in range(start_attempt, start_attempt + updates):
        lr = base_lr * min((attempt + 1) / warmup_attempts, 1.0)
        for group in optimizer.param_groups:
            group["lr"] = lr
        optimizer.zero_grad(set_to_none=True)
        chosen = [
            batches[(attempt * accumulation + index) % len(batches)]
            for index in range(accumulation)
        ]
        supervised_tokens = sum((labels != -100).sum().item() for _, labels in chosen)
        if not supervised_tokens:
            raise ValueError("累积组没有监督token")
        total_loss = 0.0
        for inputs, labels in chosen:
            with precision_context(device, precision):
                loss_sum, _ = token_loss(model(inputs), labels)
                weighted_loss = loss_sum / supervised_tokens
            if not torch.isfinite(weighted_loss):
                raise RuntimeError("loss非有限，停止更新并排查")
            scaler.scale(weighted_loss).backward()
            total_loss += weighted_loss.detach().item()
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(
            [parameter for parameter in model.parameters() if parameter.requires_grad],
            max_norm=1.0,
            error_if_nonfinite=precision != "fp16",
        )
        previous_scale = scaler.get_scale()
        scaler.step(optimizer)
        scaler.update()
        applied = scaler.get_scale() >= previous_scale
        history.append(
            {"attempt": attempt + 1, "loss": total_loss, "lr": lr, "applied": applied}
        )
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    return {
        "history": history,
        "elapsed_seconds": time.perf_counter() - start,
        "scaler": scaler,
    }


@torch.inference_mode()
def evaluate_loss(model, rows, device, batch_size=32):
    model.eval()
    total = 0.0
    count = 0
    for start in range(0, len(rows), batch_size):
        inputs, labels = make_batch(rows[start : start + batch_size], device)
        loss, tokens = token_loss(model(inputs), labels)
        total += loss.item()
        count += tokens
    if count == 0:
        raise ValueError("评估不能空")
    return total / count


@torch.inference_mode()
def evaluate_generation(model, rows, device, batch_size=32):
    if not rows or type(batch_size) is not int or batch_size < 1:
        raise ValueError("评估数据不能为空，batch_size需正整数")
    model.eval()
    details = []
    for start in range(0, len(rows), batch_size):
        current = rows[start : start + batch_size]
        if len({len(row["prompt"]) for row in current}) != 1:
            raise ValueError("本例批量生成需要等长提示")
        inputs = torch.tensor([encode(row["prompt"]) for row in current], device=device)
        generated = []
        ended = torch.zeros(len(current), dtype=torch.bool, device=device)
        for _ in range(4):
            next_ids = model(inputs)[:, -1].argmax(-1)
            next_ids = torch.where(ended, EOS_ID, next_ids)
            generated.append(next_ids)
            ended = ended | (next_ids == EOS_ID)
            inputs = torch.cat([inputs, next_ids[:, None]], dim=1)
        outputs = torch.stack(generated, dim=1).cpu().tolist()
        for row, predicted in zip(current, outputs, strict=True):
            if EOS_ID in predicted:
                predicted = predicted[: predicted.index(EOS_ID) + 1]
            gold = encode(row["answer"])
            details.append(
                {
                    "source_group": row["source_group"],
                    "prompt": " ".join(row["prompt"]),
                    "expected": gold,
                    "predicted": predicted,
                    "passed": predicted == gold,
                }
            )
    return {
        "n": len(details),
        "passed": sum(row["passed"] for row in details),
        "details": details,
    }
