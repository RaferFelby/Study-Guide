"""调用本地假 API，验证结构化结果，并比较固定的 Prompt 评估夹具。"""

from api_client import ApiError, call_api, extract_output_text
from evaluation import compare_prompt_versions, demo_records
from fake_provider import run_fake_provider
from structured_output import OutputValidationError, parse_and_validate


def main() -> None:
    ticket_text = "订单扣费两次，我申请退款。"
    payload = {
        "model": "local-demo-model",
        "input": [
            {"role": "developer", "content": "分类客服请求并按规定的 JSON 字段返回。"},
            {"role": "user", "content": ticket_text},
        ],
    }

    with run_fake_provider() as base_url:
        cache: dict[str, dict] = {}
        result = None
        repeated_result = None
        try:
            result = call_api(base_url, payload, "demo-key-no-charge", cache=cache)
            output_text = extract_output_text(result.response)
            prediction = parse_and_validate(output_text, ticket_text)
            repeated_result = call_api(
                base_url, payload, "demo-key-no-charge", cache=cache
            )
        except (ApiError, OutputValidationError) as error:
            print(f"请求失败，使用可观察的降级结果：{error}")
            prediction = {"category": "unknown", "priority": 0, "evidence": ""}

        print("结构化结果：", prediction)
        print("首次请求次数：", result.attempts if result else 0)
        print(
            "重复请求命中缓存：",
            repeated_result.cache_hit if repeated_result else False,
        )

        retry_payload = {"model": "local-demo-model", "input": "retry-once"}
        retry_result = call_api(
            base_url,
            retry_payload,
            "demo-key-no-charge",
            max_attempts=3,
            backoff_seconds=0,
        )
        print("限流后成功所用尝试次数：", retry_result.attempts)

    report = compare_prompt_versions(
        demo_records(),
        input_price_per_million=1.0,
        output_price_per_million=4.0,
    )
    for prompt_version, metrics in report.items():
        print(prompt_version, metrics)
    print("注意：Prompt 对照的输出与单价均为固定教学夹具，不是模型实测或当前厂商报价。")


if __name__ == "__main__":
    main()
