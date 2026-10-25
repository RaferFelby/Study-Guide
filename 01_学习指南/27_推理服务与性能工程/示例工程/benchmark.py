"""闭环有限并发压测；模拟后端单位吞吐，不是LLM token/s。"""

import argparse
import json
import platform
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

from client import NoRedirect, percentile, stream_request, validate_address


def run_benchmark(address, requests=20, concurrency=1, output_units=8):
    validate_address(address)
    if (
        type(requests) is not int
        or not 1 <= requests <= 200
        or type(concurrency) is not int
        or not 1 <= concurrency <= 16
        or type(output_units) is not int
        or not 1 <= output_units <= 32
    ):
        raise ValueError("requests 1..200/concurrency 1..16/output_units 1..32需整数")
    prompt = "eight input units for a fixed toy workload"
    with build_opener(ProxyHandler({}), NoRedirect()).open(
        address + "/health", timeout=3
    ) as response:
        raw = response.read(4097)
    if len(raw) > 4096:
        raise ValueError("服务健康响应过大")
    service = json.loads(raw)
    if (
        not isinstance(service, dict)
        or service.get("status") != "ready"
        or service.get("backend") != "synthetic_delay_not_llm"
    ):
        raise ValueError("此压测只接受已说明的模拟后端，真实模型需重建计量口径")
    warmup = stream_request(address, prompt, output_units)
    if not warmup["success"]:
        raise RuntimeError("预热失败，不能继续将该批记为有效压测")
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [
            pool.submit(stream_request, address, prompt, output_units)
            for _ in range(requests)
        ]
        results = [future.result() for future in futures]
    seconds = time.perf_counter() - started
    successes = [row for row in results if row["success"]]
    latencies = [row["elapsed_seconds"] for row in successes]
    ttfts = [
        row["ttft_seconds"] for row in successes if row["ttft_seconds"] is not None
    ]
    tpots = [
        row["tpot_seconds"] for row in successes if row["tpot_seconds"] is not None
    ]
    delivered = sum(row["output_units"] for row in successes)
    return {
        "scope": "actual_local_http_synthetic_backend_not_llm_tokens",
        "service": service,
        "environment": {
            "python": platform.python_version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "system": platform.platform(),
            "gpu": "not_used",
            "peak_memory_bytes": None,
        },
        "conditions": {
            "requests": requests,
            "concurrency": concurrency,
            "input_units": len(prompt.split()),
            "target_output_units": output_units,
            "load": "closed_loop_thread_workers_no_retry",
            "warmup_requests_excluded": 1,
        },
        "summary": {
            "successes": len(successes),
            "failures": requests - len(successes),
            "failure_rate": (requests - len(successes)) / requests,
            "batch_seconds": seconds,
            "completed_output_units_per_second": delivered / seconds,
            "latency_p50_seconds": percentile(latencies, 0.5) if latencies else None,
            "latency_p95_seconds": percentile(latencies, 0.95) if latencies else None,
            "ttft_p50_seconds": percentile(ttfts, 0.5) if ttfts else None,
            "ttft_p95_seconds": percentile(ttfts, 0.95) if ttfts else None,
            "tpot_p50_seconds": percentile(tpots, 0.5) if tpots else None,
        },
        "results": results,
        "limits": [
            "后端为人工延迟片段",
            "吞吐排除失败请求已送出的部分片段，失败单列",
            "分位数仅基于完整成功请求",
            "无GPU与内存实测",
            "不是固定到达率或饱和吞吐基准",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="仅本机模拟服务压测")
    parser.add_argument("--address", default="http://127.0.0.1:8770")
    parser.add_argument("--requests", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--output-units", type=int, default=8)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run_benchmark(
        args.address, args.requests, args.concurrency, args.output_units
    )
    if args.output is not None:
        with args.output.open("x", encoding="utf-8") as output:
            json.dump(report, output, ensure_ascii=False, indent=2)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
