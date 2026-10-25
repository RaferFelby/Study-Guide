"""对称INT4算术示例，不实现AWQ/GPTQ或真实低位GPU存储。"""

import math


def symmetric_int4(weights):
    if (
        not weights
        or any(not math.isfinite(weight) for weight in weights)
        or all(weight == 0 for weight in weights)
    ):
        raise ValueError("示例权重不能空或全零")
    scale = max(abs(weight) for weight in weights) / 7
    integers = [max(-7, min(7, round(weight / scale))) for weight in weights]
    restored = [integer * scale for integer in integers]
    return {"scale": scale, "integers": integers, "restored": restored}


def compare_task():
    weights = [0.31, 0.89]
    result = symmetric_int4(weights)
    cases = [
        ([1.0, -0.32], True),
        ([1.0, -0.4], False),
        ([-1.0, 0.32], False),
        ([-1.0, 0.4], True),
    ]
    details = []
    for inputs, expected in cases:
        original = (
            sum(value * weight for value, weight in zip(inputs, weights, strict=True))
            >= 0
        )
        quantized = (
            sum(
                value * weight
                for value, weight in zip(inputs, result["restored"], strict=True)
            )
            >= 0
        )
        details.append(
            {
                "inputs": inputs,
                "expected": expected,
                "fp_passed": original == expected,
                "int4_passed": quantized == expected,
            }
        )
    return {
        "scope": "four_fixed_arithmetic_cases_not_llm_quantization",
        "quantization": result,
        "n": len(cases),
        "fp_passed": sum(case["fp_passed"] for case in details),
        "int4_passed": sum(case["int4_passed"] for case in details),
        "details": details,
    }
