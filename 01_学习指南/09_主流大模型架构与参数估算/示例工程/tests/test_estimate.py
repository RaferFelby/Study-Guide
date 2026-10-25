"""估算脚本的公式、边界和输入校验测试。"""

import pytest

from estimate import estimate_kv_cache_bytes, estimate_parameter_count


@pytest.fixture
def tiny_config():
    return {
        "hidden_size": 8,
        "num_hidden_layers": 2,
        "num_attention_heads": 2,
        "num_key_value_heads": 1,
        "intermediate_size": 16,
        "vocab_size": 10,
        "tie_word_embeddings": False,
        "gated_mlp": True,
        "attention_bias": False,
        "mlp_bias": False,
        "lm_head_bias": False,
    }


def test_parameter_estimate_counts_gqa_swiglu_and_untied_embeddings(tiny_config):
    assert estimate_parameter_count(tiny_config) == 1352


def test_parameter_estimate_shares_embedding_when_config_requests_it(tiny_config):
    tiny_config["tie_word_embeddings"] = True

    assert estimate_parameter_count(tiny_config) == 1272


def test_kv_cache_estimate_scales_with_batch_sequence_and_dtype(tiny_config):
    cache_bytes = estimate_kv_cache_bytes(
        tiny_config,
        batch_size=2,
        sequence_length=3,
        bytes_per_element=2,
    )

    assert cache_bytes == 192


def test_parameter_estimate_rejects_non_divisible_attention_heads(tiny_config):
    tiny_config["num_attention_heads"] = 3

    with pytest.raises(ValueError, match="hidden_size must be divisible"):
        estimate_parameter_count(tiny_config)


def test_kv_cache_estimate_rejects_zero_batch_size(tiny_config):
    with pytest.raises(ValueError, match="batch_size must be a positive integer"):
        estimate_kv_cache_bytes(
            tiny_config,
            batch_size=0,
            sequence_length=3,
            bytes_per_element=2,
        )
