import html
import math
from collections import Counter
from decimal import Decimal
from pathlib import Path


def percentile_nearest_rank(values, fraction):
    if not values or not 0 < fraction <= 1:
        raise ValueError("分位计算需非空数据和(0,1]比例")
    if any(not math.isfinite(value) or value < 0 for value in values):
        raise ValueError("耗时须非负有限")
    ordered = sorted(values)
    return ordered[math.ceil(len(ordered) * fraction) - 1]


def summarize(rows):
    if not rows:
        raise ValueError("报告不能使用空任务集")
    n = len(rows)
    errors = Counter(
        row["output"].get("error_code")
        for row in rows
        if row["output"]["status"] == "failed"
    )
    successful = sum(row["output"]["status"] != "failed" for row in rows)
    return {
        "n": n,
        "availability": successful / n,
        "quality": sum(row["quality_passed"] for row in rows) / n,
        "p95_ms": percentile_nearest_rank([row["duration_ms"] for row in rows], 0.95),
        "input_tokens_simulated": sum(row["input_tokens"] for row in rows),
        "output_tokens_simulated": sum(row["output_tokens"] for row in rows),
        "cost_units": str(
            sum((Decimal(row["cost_units"]) for row in rows), Decimal(0))
        ),
        "cache_hits": sum(row["cache_hit"] for row in rows),
        "errors": dict(errors),
    }


def check_slo(rows, availability_target=0.99, latency_target_ms=250):
    if not rows or not 0 < availability_target <= 1 or latency_target_ms <= 0:
        raise ValueError("需要非空窗口、合法可用性与延迟目标")
    good = sum(
        row["output"]["status"] != "failed" and row["duration_ms"] <= latency_target_ms
        for row in rows
    )
    bad = len(rows) - good
    allowed = (1 - availability_target) * len(rows)
    return {
        "window_n": len(rows),
        "good": good,
        "bad": bad,
        "good_fraction": good / len(rows),
        "target": availability_target,
        "latency_target_ms": latency_target_ms,
        "allowed_bad": allowed,
        "budget_remaining": allowed - bad,
        "alert": good / len(rows) < availability_target,
        "action": "暂停扩量，检查错误和慢阶段；回滚最近配置或降级为只读拒答"
        if bad > allowed
        else "继续观察",
    }


def write_dashboard(path: Path, experiments: dict):
    columns = [
        "n",
        "availability",
        "quality",
        "p95_ms",
        "input_tokens_simulated",
        "output_tokens_simulated",
        "cost_units",
        "cache_hits",
        "errors",
    ]
    headers = "".join(f"<th>{html.escape(name)}</th>" for name in ["variant", *columns])
    body = []
    for name, experiment in experiments.items():
        values = [name, *(experiment["summary"][column] for column in columns)]
        body.append(
            "<tr>"
            + "".join(f"<td>{html.escape(str(value))}</td>" for value in values)
            + "</tr>"
        )
    content = (
        "<!doctype html><html lang='zh-CN'><meta charset='utf-8'><title>离线可观测性报告</title><style>body{font:16px sans-serif;margin:32px}table{border-collapse:collapse}td,th{border:1px solid #aaa;padding:10px}th{background:#eef}td{vertical-align:top}</style><h1>离线可观测性报告</h1><p>合成流量；耗时为模拟时钟，token为字节计数夹具，成本为虚构单位。不是线上仪表盘或供应商账单。</p><table><thead><tr>"
        + headers
        + "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table></html>"
    )
    with path.open("x", encoding="utf-8") as stream:
        stream.write(content)
