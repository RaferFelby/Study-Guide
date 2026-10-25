"""从模型结构配置估算稠密 Transformer 参数量和普通 KV Cache。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

BYTES_PER_DTYPE = {
    "bfloat16": 2,
    "float16": 2,
    "float32": 4,
}
GIBIBYTE = 1024**3


def validate_config(config: dict[str, Any]) -> None:
    """检查估算公式需要的配置字段和维度关系。"""
    required_positive = (
        "hidden_size",
        "num_hidden_layers",
        "num_attention_heads",
        "num_key_value_heads",
        "intermediate_size",
        "vocab_size",
    )
    for key in required_positive:
        value = config.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError(f"{key} must be a positive integer")

    hidden_size = config["hidden_size"]
    attention_heads = config["num_attention_heads"]
    key_value_heads = config["num_key_value_heads"]
    if hidden_size % attention_heads != 0:
        raise ValueError("hidden_size must be divisible by num_attention_heads")
    if attention_heads % key_value_heads != 0:
        raise ValueError("num_attention_heads must be divisible by num_key_value_heads")

    for key in (
        "tie_word_embeddings",
        "gated_mlp",
        "attention_bias",
        "mlp_bias",
        "lm_head_bias",
    ):
        if not isinstance(config.get(key), bool):
            raise TypeError(f"{key} must be a boolean")


def estimate_parameter_count(config: dict[str, Any]) -> int:
    """估算模型参数数目；不含量化元数据和模型实现的额外模块。"""
    validate_config(config)
    hidden_size = config["hidden_size"]
    num_layers = config["num_hidden_layers"]
    num_attention_heads = config["num_attention_heads"]
    num_key_value_heads = config["num_key_value_heads"]
    head_dim = hidden_size // num_attention_heads
    key_value_dim = num_key_value_heads * head_dim
    intermediate_size = config["intermediate_size"]

    # Q、K、V 和输出投影。GQA 只缩小 K/V 投影，Q 和输出投影仍用 hidden_size。
    attention_parameters_per_layer = (
        2 * hidden_size * hidden_size + 2 * hidden_size * key_value_dim
    )
    if config["attention_bias"]:
        attention_parameters_per_layer += 2 * hidden_size + 2 * key_value_dim

    # SwiGLU 有 gate、up、down 三个矩阵；普通两层 MLP 有两个矩阵。
    mlp_matrix_count = 3 if config["gated_mlp"] else 2
    mlp_parameters_per_layer = mlp_matrix_count * hidden_size * intermediate_size
    if config["mlp_bias"]:
        mlp_parameters_per_layer += (
            (2 * intermediate_size + hidden_size)
            if config["gated_mlp"]
            else intermediate_size + hidden_size
        )

    # 两个 RMSNorm 各有一组 scale；Block 堆叠后再有一个 final RMSNorm。
    norm_parameters = (2 * num_layers + 1) * hidden_size
    input_embedding_parameters = config["vocab_size"] * hidden_size
    output_parameters = (
        0 if config["tie_word_embeddings"] else config["vocab_size"] * hidden_size
    )
    output_bias_parameters = 0
    if config["lm_head_bias"]:
        output_bias_parameters = config["vocab_size"]

    return (
        num_layers * (attention_parameters_per_layer + mlp_parameters_per_layer)
        + norm_parameters
        + input_embedding_parameters
        + output_parameters
        + output_bias_parameters
    )


def estimate_kv_cache_bytes(
    config: dict[str, Any],
    *,
    batch_size: int,
    sequence_length: int,
    bytes_per_element: int,
) -> int:
    """估算普通 K/V 缓存的原始张量字节数，不含运行时额外开销。"""
    validate_config(config)
    for name, value in (
        ("batch_size", batch_size),
        ("sequence_length", sequence_length),
        ("bytes_per_element", bytes_per_element),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError(f"{name} must be a positive integer")

    head_dim = config["hidden_size"] // config["num_attention_heads"]
    return (
        2
        * config["num_hidden_layers"]
        * batch_size
        * sequence_length
        * config["num_key_value_heads"]
        * head_dim
        * bytes_per_element
    )


def load_config(path: Path) -> dict[str, Any]:
    """读取 JSON 配置并为解析错误补充文件路径。"""
    try:
        with path.open(encoding="utf-8") as config_file:
            config = json.load(config_file)
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON in {path}: {error}") from error
    if not isinstance(config, dict):
        raise TypeError(f"configuration in {path} must be a JSON object")
    validate_config(config)
    return config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="估算稠密 Decoder Transformer 参数量和普通 KV Cache。"
    )
    parser.add_argument("config", type=Path, help="模型结构 JSON 文件路径")
    parser.add_argument("--batch-size", type=int, default=1, help="并发序列数")
    parser.add_argument(
        "--sequence-length", type=int, default=4096, help="缓存 token 数"
    )
    parser.add_argument(
        "--dtype",
        choices=tuple(BYTES_PER_DTYPE),
        default="bfloat16",
        help="权重和 KV 元素精度，用于估算字节数",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(args.config)
    if args.batch_size < 1 or args.sequence_length < 1:
        raise SystemExit("--batch-size and --sequence-length must be positive")

    parameter_count = estimate_parameter_count(config)
    weight_bytes = parameter_count * BYTES_PER_DTYPE[args.dtype]
    cache_bytes = estimate_kv_cache_bytes(
        config,
        batch_size=args.batch_size,
        sequence_length=args.sequence_length,
        bytes_per_element=BYTES_PER_DTYPE[args.dtype],
    )
    print(f"模型：{config.get('model_name', args.config.stem)}")
    print(f"估算参数量：{parameter_count:,} ({parameter_count / 1e9:.3f} B)")
    print(f"{args.dtype} 权重理论存储：{weight_bytes / GIBIBYTE:.2f} GiB")
    print(
        f"{args.dtype} 普通 KV Cache 理论存储"
        f"（batch={args.batch_size}, tokens={args.sequence_length}）："
        f"{cache_bytes / GIBIBYTE:.2f} GiB"
    )
    print("未计入激活、临时工作区、量化元数据、显存碎片和服务框架开销。")


if __name__ == "__main__":
    main()
