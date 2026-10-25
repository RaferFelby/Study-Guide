from decimal import Decimal

RATE_VERSION = "synthetic-rates-v1"
RATES = {
    "large-mock": (Decimal("0.001"), Decimal("0.002")),
    "small-mock": (Decimal("0.0002"), Decimal("0.0004")),
}


def model_cost(model: str, input_tokens: int, output_tokens: int):
    if model not in RATES:
        raise ValueError("未知模型费率，不能默认为免费")
    for value in (input_tokens, output_tokens):
        if type(value) is not int or value < 0:
            raise ValueError("token计数必须为非负整数")
    input_rate, output_rate = RATES[model]
    return input_rate * input_tokens + output_rate * output_tokens


def allocate_infrastructure(total_units: Decimal, request_count: int):
    if (
        not total_units.is_finite()
        or total_units < 0
        or type(request_count) is not int
        or request_count <= 0
    ):
        raise ValueError("分摊需非负有限总成本与正请求数")
    return total_units / request_count
