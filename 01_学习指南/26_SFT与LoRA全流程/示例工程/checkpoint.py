"""完整训练状态与推理适配器分开保存；仅读取自己可信生成的文件。"""

import copy
import hashlib

import torch

from model import add_lora


def state_digest(model):
    digest = hashlib.sha256()
    for name, value in sorted(model.state_dict().items()):
        tensor = value.detach().cpu().contiguous()
        digest.update(name.encode("utf-8"))
        digest.update(str((tensor.dtype, tuple(tensor.shape))).encode("utf-8"))
        digest.update(tensor.numpy().tobytes())
    return digest.hexdigest()


def save_training_state(path, model, optimizer, scaler, completed_attempts, config):
    if path.exists():
        raise FileExistsError("拒绝覆盖训练状态")
    state = {
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict(),
        "scaler": scaler.state_dict(),
        "completed_attempts": completed_attempts,
        "config": config,
        "cpu_rng": torch.get_rng_state(),
        "cuda_rng": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
    }
    torch.save(state, path)


def load_training_state(path, model, optimizer, scaler, expected_config):
    state = torch.load(path, map_location="cpu", weights_only=True)
    if state["config"] != expected_config:
        raise ValueError("恢复配置与训练状态不一致")
    if state["cuda_rng"] and len(state["cuda_rng"]) != torch.cuda.device_count():
        raise ValueError("CUDA设备数量与随机状态不一致")
    model.load_state_dict(state["model"])
    optimizer.load_state_dict(state["optimizer"])
    scaler.load_state_dict(state["scaler"])
    torch.set_rng_state(state["cpu_rng"])
    if state["cuda_rng"]:
        torch.cuda.set_rng_state_all(state["cuda_rng"])
    return state["completed_attempts"]


def save_adapter(path, model, base_digest, config):
    if path.exists():
        raise FileExistsError("拒绝覆盖推理适配器")
    weights = {
        name: parameter.detach().cpu()
        for name, parameter in model.named_parameters()
        if "lora_" in name
    }
    if not weights:
        raise ValueError("没有LoRA参数")
    torch.save({"base_digest": base_digest, "config": config, "weights": weights}, path)


def load_adapter(path, base_model, base_digest):
    if state_digest(base_model) != base_digest:
        raise ValueError("实际Base权重与提供的摘要不一致")
    state = torch.load(path, map_location="cpu", weights_only=True)
    if state["base_digest"] != base_digest:
        raise ValueError("适配器对应的Base不一致")
    config = state["config"]
    result = add_lora(
        copy.deepcopy(base_model),
        config["rank"],
        tuple(config["targets"]),
        config["dropout"],
    )
    parameters = dict(result.named_parameters())
    expected = {name for name in parameters if "lora_" in name}
    if set(state["weights"]) != expected:
        raise ValueError("适配器参数名不完整")
    with torch.no_grad():
        for name, value in state["weights"].items():
            parameters[name].copy_(value)
    return result
